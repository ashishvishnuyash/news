from __future__ import annotations

import argparse
import asyncio
import concurrent.futures
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from india_sources import IndiaCompleteNewsSource, is_publisher_placeholder_or_logo
from models import RewrittenArticle, SourceArticle
from publisher import PublicationLedger
from rewriter import OpenRouterRewriter, build_source_fallback, clean_editorial_text

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / "backend" / ".env")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://azureuser:Cywar%40exe248@newsql.postgres.database.azure.com:5432/postgres",
)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free").strip()


def configure_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")


def slugify(text_val: str) -> str:
    """Generate a clean URL slug from title."""
    s = text_val.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s[:150].strip("-")


async def get_valid_author_id(session: AsyncSession) -> int:
    """Find an active journalist or admin user ID to assign as article author."""
    res = await session.execute(
        text("SELECT id FROM users WHERE role IN ('JOURNALIST', 'ADMIN', 'SUPER_ADMIN') ORDER BY id ASC LIMIT 1")
    )
    user_id = res.scalar()
    if not user_id:
        res_any = await session.execute(text("SELECT id FROM users ORDER BY id ASC LIMIT 1"))
        user_id = res_any.scalar()
    if not user_id:
        raise RuntimeError("No users found in database to assign as article author.")
    return user_id


async def article_exists_in_db(session: AsyncSession, title: str, slug: str) -> bool:
    """Check if an article with similar title or slug already exists in PostgreSQL."""
    res = await session.execute(
        text("SELECT 1 FROM articles WHERE lower(title) = lower(:title) OR slug = :slug LIMIT 1"),
        {"title": title, "slug": slug},
    )
    return res.scalar() is not None


async def push_to_database(
    session: AsyncSession,
    rewritten: RewrittenArticle,
    source: SourceArticle,
    author_id: int,
) -> dict[str, Any]:
    """Insert rewritten article directly into PostgreSQL articles table with status PUBLISHED."""
    base_slug = slugify(rewritten.title)
    if not base_slug:
        base_slug = f"india-news-{int(source.published_at.timestamp())}"

    # Ensure slug uniqueness
    slug = base_slug
    counter = 1
    while await article_exists_in_db(session, rewritten.title, slug):
        counter += 1
        slug = f"{base_slug}-{counter}"

    md_content = rewritten.content_markdown.strip()
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    pub_at = source.published_at.replace(tzinfo=None) if source.published_at else now_utc

    tags_str = ", ".join(rewritten.tags) if rewritten.tags else "India, News, Special Report"

    query = text(
        """
        INSERT INTO articles (
            title, slug, content, summary, status, category,
            image_url, image_caption, tags, view_count, is_pinned,
            is_breaking, created_at, updated_at, published_at, author_id
        ) VALUES (
            :title, :slug, :content, :summary, :status, :category,
            :image_url, :image_caption, :tags, :view_count, :is_pinned,
            :is_breaking, :created_at, :updated_at, :published_at, :author_id
        ) RETURNING id, title, slug, status, category
        """
    )

    clean_img = None
    clean_caption = None
    if source.image_url and not is_publisher_placeholder_or_logo(source.image_url):
        clean_img = source.image_url.strip()
        clean_caption = "Special Report"

    params = {
        "title": rewritten.title,
        "slug": slug,
        "content": md_content,
        "summary": rewritten.summary[:500] if rewritten.summary else None,
        "status": "PUBLISHED",
        "category": rewritten.category or "General",
        "image_url": clean_img,
        "image_caption": clean_caption,
        "tags": tags_str,
        "view_count": 0,
        "is_pinned": False,
        "is_breaking": False,
        "created_at": now_utc,
        "updated_at": now_utc,
        "published_at": pub_at,
        "author_id": author_id,
    }

    result = await session.execute(query, params)
    await session.commit()
    row = result.fetchone()
    return {"id": row[0], "title": row[1], "slug": row[2], "status": row[3], "category": row[4]}


def process_single_article(
    source_aggregator: IndiaCompleteNewsSource,
    rewriter: OpenRouterRewriter | None,
    article: SourceArticle,
) -> tuple[RewrittenArticle, SourceArticle]:
    """Enrich full body text and lead image, then rewrite with AI or clean editorial fallback."""
    source_aggregator.enrich(article)
    body_len = len((article.text or "").strip())

    rewritten = None
    if rewriter and body_len >= 250:
        try:
            rewritten = rewriter.rewrite(article)
        except Exception as exc:
            pass

    if not rewritten:
        rewritten = build_source_fallback(article)

    return rewritten, article


async def main() -> None:
    configure_console()

    parser = argparse.ArgumentParser(description="Scrape and AI-rewrite complete India-centric news from Aug 13 to present.")
    parser.add_argument("--since", type=str, default="2026-08-13", help="Start date (YYYY-MM-DD), default: 2026-08-13")
    parser.add_argument("--max", type=int, default=500, help="Maximum articles to process")
    parser.add_argument("--workers", type=int, default=6, help="Concurrent worker threads for enrichment/rewriting")
    args = parser.parse_args()

    try:
        start_date = datetime.strptime(args.since, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        start_date = datetime(2026, 8, 13, 0, 0, 0, tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)

    print("=" * 70, flush=True)
    print(" INDIA-CENTRIC FULL NEWS SCRAPER & AI REWRITING PIPELINE", flush=True)
    print(f" Target Date Range: {start_date.strftime('%Y-%m-%d %H:%M:%S UTC')} -> {now.strftime('%Y-%m-%d %H:%M:%S UTC')}", flush=True)
    print(f" Max Articles Cap: {args.max} | Workers: {args.workers}", flush=True)
    print(f" Target DB: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}", flush=True)
    print("=" * 70 + "\n", flush=True)

    # 1. Discover all articles in parallel
    t0 = time.time()
    source_aggregator = IndiaCompleteNewsSource(timeout=15)
    discovered = source_aggregator.discover_all(start_date, now, max_articles=args.max)

    if not discovered:
        print("No articles discovered in the specified timeframe.", flush=True)
        return

    print(f"\n[+] Total Discovered Articles: {len(discovered)} (discovered in {time.time() - t0:.1f}s)", flush=True)

    # 2. Setup AI Rewriter
    rewriter = None
    if OPENROUTER_API_KEY:
        try:
            rewriter = OpenRouterRewriter(api_key=OPENROUTER_API_KEY, model=OPENROUTER_MODEL, timeout=25)
            print(f"[+] OpenRouter AI Rewriter initialized (model: {OPENROUTER_MODEL})", flush=True)
        except Exception as exc:
            print(f"[!] Warning: AI Rewriter init failed ({exc}); using smart editorial fallback.", flush=True)

    # 3. Setup Database Connection & Ledger
    engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True, pool_recycle=300)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    ledger = PublicationLedger(BASE_DIR / "publications.sqlite3")

    async with async_session() as init_session:
        author_id = await get_valid_author_id(init_session)
    print(f"[+] Assigned author ID: {author_id}\n", flush=True)

    inserted = 0
    skipped = 0
    failed = 0
    category_counts: dict[str, int] = {}

    print("-" * 70, flush=True)
    print("Processing Pipeline: Parallel Extraction & AI Rewrite -> Ingest to DB", flush=True)
    print("-" * 70, flush=True)

    # Filter out articles already in ledger before heavy network extraction
    to_process: list[SourceArticle] = []
    for article in discovered:
        if ledger.contains(article):
            skipped += 1
            continue
        to_process.append(article)

    print(f"[*] Remaining new candidates to process: {len(to_process)} (Skipped ledger matches: {skipped})\n", flush=True)

    # Process candidates in parallel batches using ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_article = {
            executor.submit(process_single_article, source_aggregator, rewriter, art): art
            for art in to_process
        }

        for idx, future in enumerate(concurrent.futures.as_completed(future_to_article), start=1):
            orig_art = future_to_article[future]
            try:
                rewritten, enriched_source = future.result()

                # Deduplication check in DB
                async with async_session() as check_session:
                    if await article_exists_in_db(check_session, rewritten.title, slugify(rewritten.title)):
                        skipped += 1
                        ledger.record(enriched_source, 0, "ALREADY_EXISTS")
                        continue

                # Insert into DB
                async with async_session() as insert_session:
                    pushed = await push_to_database(insert_session, rewritten, enriched_source, author_id)
                    ledger.record(enriched_source, int(pushed["id"]), str(pushed["status"]))
                    inserted += 1
                    cat = pushed["category"]
                    category_counts[cat] = category_counts.get(cat, 0) + 1
                    print(
                        f"[{idx}/{len(to_process)}] SAVED #{pushed['id']} [{cat}] {pushed['title'][:60]} (slug: {pushed['slug']})",
                        flush=True,
                    )

            except Exception as exc:
                failed += 1
                print(f"[{idx}/{len(to_process)}] [!] FAILED for '{orig_art.title[:45]}': {exc}", file=sys.stderr, flush=True)

    ledger.close()
    await engine.dispose()

    print("\n" + "=" * 70, flush=True)
    print(" INGESTION COMPLETE", flush=True)
    print(f" - Total Discovered: {len(discovered)}", flush=True)
    print(f" - Inserted into PostgreSQL DB: {inserted}", flush=True)
    print(f" - Skipped (Duplicates/Existing): {skipped}", flush=True)
    print(f" - Failed: {failed}", flush=True)
    if category_counts:
        print(" - Categories Ingested:", flush=True)
        for cat, cnt in sorted(category_counts.items(), key=lambda x: -x[1]):
            print(f"     * {cat}: {cnt}", flush=True)
    print("=" * 70, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
