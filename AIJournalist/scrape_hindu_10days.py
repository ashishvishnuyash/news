from __future__ import annotations

import asyncio
import html
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from markdown import markdown
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from hindu_source import TheHinduRSSSource
from models import RewrittenArticle, SourceArticle
from publisher import PublicationLedger
from rewriter import OpenRouterRewriter, build_source_fallback

BASE_DIR = Path(__file__).resolve().parent
# Load environment variables from AIJournalist/.env and backend/.env
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / "backend" / ".env")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://azureuser:Cywar%40exe248@newsql.postgres.database.azure.com:5432/postgres",
)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free").strip()


def slugify(text_val: str) -> str:
    """Generate a clean URL slug from title."""
    s = text_val.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s[:150].strip("-")


def configure_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")


async def get_valid_author_id(session: AsyncSession) -> int:
    """Find a JOURNALIST, ADMIN, or SUPER_ADMIN user ID in the database."""
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
    """Check if an article with the same title or slug already exists in PostgreSQL."""
    res = await session.execute(
        text("SELECT 1 FROM articles WHERE lower(title) = lower(:title) OR slug = :slug LIMIT 1"),
        {"title": title, "slug": slug},
    )
    return res.scalar() is not None


async def push_rewritten_to_db(
    session: AsyncSession, rewritten: RewrittenArticle, source: SourceArticle, author_id: int
) -> dict[str, Any]:
    """Insert rewritten article directly into PostgreSQL articles table without any source citations."""
    base_slug = slugify(rewritten.title)
    if not base_slug:
        base_slug = f"article-{int(source.published_at.timestamp())}"

    # Ensure slug uniqueness
    slug = base_slug
    counter = 1
    while await article_exists_in_db(session, rewritten.title, slug):
        counter += 1
        slug = f"{base_slug}-{counter}"

    # Store clean pure Markdown (.md) format in database content field
    md_content = rewritten.content_markdown.strip()
    md_content = re.sub(r"Source:.*$", "", md_content, flags=re.IGNORECASE | re.MULTILINE).strip()

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    pub_at = source.published_at.replace(tzinfo=None) if source.published_at else now

    tags_str = ", ".join(rewritten.tags) if rewritten.tags else "News, Special Report"

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

    params = {
        "title": rewritten.title,
        "slug": slug,
        "content": md_content,
        "summary": rewritten.summary[:500] if rewritten.summary else None,

        "status": "PUBLISHED",
        "category": rewritten.category or getattr(source, "category", "General"),
        "image_url": source.image_url or None,
        "image_caption": source.image_caption or None,
        "tags": tags_str,
        "view_count": 0,
        "is_pinned": False,
        "is_breaking": False,
        "created_at": now,
        "updated_at": now,
        "published_at": pub_at,
        "author_id": author_id,
    }

    result = await session.execute(query, params)
    await session.commit()
    row = result.fetchone()
    return {"id": row[0], "title": row[1], "slug": row[2], "status": row[3], "category": row[4]}


async def run_scrape(days: int = 10, max_articles: int = 500) -> None:
    configure_console()
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)

    print(f"============================================================")
    print(f" Scraping full Hindu news & AI Rewriting (No Source Citations)")
    print(f" Range: {start_date.strftime('%Y-%m-%d %H:%M:%S UTC')} -> {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f" Target DB: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}")
    print(f"============================================================\n")

    source = TheHinduRSSSource(timeout=30)
    discovered = source.discover(start_date, now, max_articles=max_articles)

    if not discovered:
        print("No news articles found in the specified 10-day window.")
        return

    print(f"\nDiscovered {len(discovered)} unique Hindu articles for the last {days} days.")

    # Initialize AI Rewriter
    rewriter = None
    if OPENROUTER_API_KEY:
        try:
            rewriter = OpenRouterRewriter(api_key=OPENROUTER_API_KEY, model=OPENROUTER_MODEL, timeout=35)
            print("OpenRouter AI Rewriter initialized successfully.")
        except Exception as exc:
            print(f"Warning: AI Rewriter init failed ({exc}); using fallback rewriter.")

    # Initialize DB engine with pool pre-ping & recycling for long-running scraper jobs
    engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True, pool_recycle=300)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    ledger = PublicationLedger(BASE_DIR / "publications.sqlite3")

    inserted = 0
    skipped = 0
    failed = 0

    async with async_session() as init_session:
        author_id = await get_valid_author_id(init_session)
    print(f"Assigned author ID {author_id} for article insertion.\n")

    print("1. Scraping full article body text\n2. Rewriting headline, summary & content\n3. Preserving image & inserting into DB...\n")
    for idx, article in enumerate(discovered, start=1):
        try:
            if ledger.contains(article):
                skipped += 1
                continue

            async with async_session() as check_session:
                if await article_exists_in_db(check_session, article.title, slugify(article.title)):
                    skipped += 1
                    ledger.record(article, 0, "ALREADY_EXISTS")
                    continue

            print(f"[{idx}/{len(discovered)}] Scraping full article: '{article.title[:65]}'...")
            source.enrich(article)

            # Step 2: AI Rewrite Title, Summary, Body text
            rewritten = None
            if rewriter and len((article.text or "").strip()) >= 300:
                try:
                    rewritten = rewriter.rewrite(article)
                    print(f"   -> AI Rewritten Title: '{rewritten.title[:65]}'")
                except Exception as exc:
                    print(f"   -> AI Rewrite fallback notice: {exc}")

            if not rewritten:
                rewritten = build_source_fallback(article)

            # Step 3: Insert into PostgreSQL Database using fresh session
            async with async_session() as insert_session:
                pushed = await push_rewritten_to_db(insert_session, rewritten, article, author_id)
                ledger.record(article, int(pushed["id"]), str(pushed["status"]))
                inserted += 1
                print(f"   -> Saved to DB: Article #{pushed['id']} [{pushed['category']}] ({pushed['title'][:50]})\n")

        except Exception as exc:
            failed += 1
            print(f"   -> Failed for '{article.title[:50]}': {exc}\n", file=sys.stderr)

    ledger.close()
    await engine.dispose()


    print(f"\n============================================================")
    print(f" SCRAPING, REWRITING & INGESTION COMPLETE")
    print(f" - Total Discovered: {len(discovered)}")
    print(f" - Inserted into DB: {inserted}")
    print(f" - Skipped (Duplicates): {skipped}")
    print(f" - Failed: {failed}")
    print(f"============================================================")


if __name__ == "__main__":
    days = 10
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        days = int(sys.argv[1])
    asyncio.run(run_scrape(days=days))
