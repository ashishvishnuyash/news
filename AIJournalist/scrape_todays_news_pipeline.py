from __future__ import annotations

import argparse
import asyncio
import calendar
import concurrent.futures
import html
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urldefrag, urlparse

import feedparser
import requests
import trafilatura
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from googlenewsdecoder import gnewsdecoder
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from models import RewrittenArticle, SourceArticle
from publisher import PublicationLedger

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / "backend" / ".env")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://azureuser:Cywar%40exe248@newsql.postgres.database.azure.com:5432/postgres",
)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}

# Explicitly EXCLUDE The Hindu AND CNN
EXCLUDED_DOMAINS_OR_SOURCES = [
    "thehindu.com",
    "thehindu",
    "th-i.thgim.com",
    "the hindu",
    "the hindu group",
    "frontline.thehindu.com",
    "sportstar.thehindu.com",
    "businessline.thehindu.com",
    "cnn.com",
    "edition.cnn.com",
    "cnn-news18",
    "news18.com/cnn",
    "cnn news",
    "cnn",
]

# Curated High-Quality RSS Feeds (NOT from The Hindu, NOT from CNN)
TODAYS_FEEDS = [
    # Indian Express
    ("Indian Express - India", "https://indianexpress.com/section/india/feed/", "Politics"),
    ("Indian Express - Business", "https://indianexpress.com/section/business/feed/", "Economy"),
    ("Indian Express - Tech", "https://indianexpress.com/section/technology/feed/", "Technology"),
    ("Indian Express - Sports", "https://indianexpress.com/section/sports/feed/", "Sports"),
    ("Indian Express - World", "https://indianexpress.com/section/world/feed/", "World"),
    ("Indian Express - Opinion", "https://indianexpress.com/section/opinion/feed/", "Opinion"),
    ("Indian Express - Entertainment", "https://indianexpress.com/section/entertainment/feed/", "Culture"),
    
    # Times of India
    ("Times of India - Top Stories", "https://timesofindia.indiatimes.com/rssfeeds/296589292.cms", "General"),
    ("Times of India - India", "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms", "Politics"),
    ("Times of India - Business", "https://timesofindia.indiatimes.com/rssfeeds/1898055.cms", "Economy"),
    ("Times of India - Tech", "https://timesofindia.indiatimes.com/rssfeeds/66949542.cms", "Technology"),
    ("Times of India - Sports", "https://timesofindia.indiatimes.com/rssfeeds/4719148.cms", "Sports"),
    ("Times of India - World", "https://timesofindia.indiatimes.com/rssfeeds/2886704.cms", "World"),
    
    # NDTV
    ("NDTV - Top Stories", "https://feeds.feedburner.com/ndtvnews-top-stories", "General"),
    ("NDTV - India", "https://feeds.feedburner.com/ndtvnews-india-news", "Politics"),
    ("NDTV - Business", "https://feeds.feedburner.com/ndtvprofit-latest", "Economy"),
    ("NDTV - Tech", "https://feeds.feedburner.com/ndtvnews-tech-gadgets", "Technology"),
    ("NDTV - Sports", "https://feeds.feedburner.com/ndtvnews-sports", "Sports"),
    ("NDTV - World", "https://feeds.feedburner.com/ndtvnews-world-news", "World"),
    
    # LiveMint
    ("LiveMint - News", "https://www.livemint.com/rss/news", "Economy"),
    ("LiveMint - Markets", "https://www.livemint.com/rss/markets", "Economy"),
    ("LiveMint - Companies", "https://www.livemint.com/rss/companies", "Economy"),
    ("LiveMint - Tech", "https://www.livemint.com/rss/technology", "Technology"),
    ("LiveMint - Sports", "https://www.livemint.com/rss/sports", "Sports"),
    
    # Hindustan Times
    ("Hindustan Times - India", "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml", "Politics"),
    ("Hindustan Times - Business", "https://www.hindustantimes.com/feeds/rss/business/rssfeed.xml", "Economy"),
    ("Hindustan Times - World", "https://www.hindustantimes.com/feeds/rss/world-news/rssfeed.xml", "World"),
    ("Hindustan Times - Tech", "https://www.hindustantimes.com/feeds/rss/tech/rssfeed.xml", "Technology"),
    ("Hindustan Times - Cricket", "https://www.hindustantimes.com/feeds/rss/cricket/rssfeed.xml", "Sports"),
    
    # Financial Express
    ("Financial Express - India", "https://www.financialexpress.com/india-news/feed/", "Politics"),
    ("Financial Express - Economy", "https://www.financialexpress.com/economy/feed/", "Economy"),
    ("Financial Express - Tech", "https://www.financialexpress.com/technology/feed/", "Technology"),
]

# Google News topics strictly excluding The Hindu and CNN
GOOGLE_NEWS_TOPICS = [
    ("India Politics & Governance", "India (politics OR parliament OR government OR supreme court) -thehindu -site:thehindu.com -cnn -site:cnn.com", "Politics"),
    ("India Economy & Markets", "India (economy OR RBI OR GDP OR inflation OR budget OR rupee OR sensex) -thehindu -site:thehindu.com -cnn -site:cnn.com", "Economy"),
    ("India Tech & Innovation", "India (technology OR AI OR semiconductors OR ISRO OR startups) -thehindu -site:thehindu.com -cnn -site:cnn.com", "Technology"),
    ("India National Affairs", "India (national OR infrastructure OR defense OR education) -thehindu -site:thehindu.com -cnn -site:cnn.com", "General"),
    ("Sports & Cricket", "India (cricket OR BCCI OR tournament OR athletics OR sports) -thehindu -site:thehindu.com -cnn -site:cnn.com", "Sports"),
    ("Global Affairs", "(world news OR geopolitics OR diplomacy OR international summit) -thehindu -site:thehindu.com -cnn -site:cnn.com", "World"),
]

PUBLISHER_PLACEHOLDER_REGEX = re.compile(
    r"("
    r"thehindu\.com"
    r"|thehindu-logo"
    r"|th-i\.thgim\.com"
    r"|cnn\.com"
    r"|ndtv\.com/.*logo"
    r"|ndtv\.com/.*placeholder"
    r"|ndtv\.com/.*default"
    r"|ndtv\.com/common/"
    r"|ndtvimg\.com/.*logo"
    r"|indianexpress\.com/.*logo"
    r"|indianexpress\.com/.*default"
    r"|indianexpress\.com/theme/"
    r"|livemint\.com/.*logo"
    r"|livemint\.com/.*default"
    r"|static\.toiimg\.com/.*default"
    r"|timesofindia.*logo"
    r"|timesofindia.*placeholder"
    r"|hindustantimes\.com/.*logo"
    r"|hindustantimes\.com/.*placeholder"
    r"|news18\.com/.*logo"
    r"|placeholder"
    r"|default_avatar"
    r"|default-news"
    r"|fallback"
    r"|dummy"
    r"|site-logo"
    r"|brand-logo"
    r"|favicon"
    r"|/logo/"
    r"|/logos/"
    r"|logo\.(png|jpg|jpeg|webp|svg|gif)"
    r"|\.ico"
    r")",
    re.IGNORECASE,
)

STOPWORDS = {
    "a", "an", "the", "in", "on", "at", "to", "for", "of", "and", "or", "by",
    "with", "is", "are", "was", "were", "be", "been", "being", "have", "has",
    "had", "do", "does", "did", "from", "as", "about", "after", "before",
    "under", "over", "into", "through", "during", "out", "up", "down", "off",
    "above", "below", "between", "against", "its", "it", "this", "that", "these",
    "those", "he", "she", "they", "we", "you", "i", "his", "her", "their", "our",
    "your", "my", "says", "said", "new", "top", "latest", "live", "news", "updates",
    "update", "report", "reports", "today", "breaking",
}

AI_REWRITE_SYSTEM_PROMPT = """You are a senior executive news journalist and editor for a prestigious digital publication.
Your task is to produce a completely rewritten, original, comprehensive, IN-DEPTH long-form news report based on the provided material.

CRITICAL QUALITY & LENGTH REQUIREMENTS:
1. HEADLINE REWRITE: Create a fresh, highly engaging, professional journalistic headline in under 140 characters. NEVER copy the original title verbatim.
2. LONG-FORM ARTICLE (MANDATORY): Produce a comprehensive report of at least 350 to 600 words with 4 to 6 substantial paragraphs.
   - Organize the article with clear Markdown section headers:
     ## Key Developments
     ## Strategic Context & Background
     ## Economic & Policy Impact
     ## Future Outlook & Next Steps
   - Ensure rich analytical depth, narrative flow, and journalistic authority.
   - Do NOT produce short summaries or stubs. The content must be detailed and extensive.
3. EXECUTIVE SUMMARY: Write a substantial 3-5 sentence overview (80-120 words).
4. NO SOURCE ATTRIBUTIONS: DO NOT mention original publisher names, news agencies (e.g. PTI, ANI, IANS, Reuters, The Hindu, CNN, NDTV, Times of India, Indian Express, Livemint, Hindustan Times), or original URLs anywhere in the output.
5. PRESERVE FACTS: Keep all real figures, names, dates, quotes, and locations accurate.
6. JSON FORMAT ONLY: Output MUST be a valid JSON object matching the exact schema below.

JSON SCHEMA:
{
  "title": "Fresh Engaging Headline Under 140 Chars",
  "summary": "Substantial 3-5 sentence overview of the news event.",
  "content_markdown": "## Key Developments\\n\\nDetailed paragraph 1...\\n\\nDetailed paragraph 2...\\n\\n## Strategic Context & Background\\n\\nDetailed paragraph 3...\\n\\n## Economic & Policy Impact\\n\\nDetailed paragraph 4...\\n\\n## Future Outlook & Next Steps\\n\\nDetailed paragraph 5...",
  "category": "Politics" | "Economy" | "Technology" | "Sports" | "General" | "World" | "Science" | "Culture" | "Opinion",
  "tags": ["Tag1", "Tag2", "Tag3", "Tag4"]
}
"""


def configure_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")


def count_words(text_val: str | None) -> int:
    if not text_val:
        return 0
    return len(re.findall(r"\b\w+\b", text_val))


def is_excluded(text_or_url: str | None) -> bool:
    if not text_or_url:
        return False
    lower = text_or_url.lower()
    if re.search(r"\bcnn\b", lower) or "cnn.com" in lower or "cnn-news18" in lower:
        return True
    if "thehindu" in lower or "the hindu" in lower or "th-i.thgim.com" in lower:
        return True
    return any(ex in lower for ex in EXCLUDED_DOMAINS_OR_SOURCES)


def clean_editorial_text(text_val: str) -> str:
    s = text_val or ""
    s = re.sub(r"^(PTI|ANI|IANS|Reuters|Bloomberg|AP|PTI-Bhasha|CNN)\s*[:-]\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\b(PTI|ANI|IANS|The Hindu|CNN|CNN-News18|NDTV|Times of India|Indian Express|Hindustan Times|Livemint|News18)\b", "", s, flags=re.IGNORECASE)
    s = re.sub(r"Source:.*$", "", s, flags=re.IGNORECASE | re.MULTILINE)
    s = re.sub(r"Also Read:.*$", "", s, flags=re.IGNORECASE | re.MULTILINE)
    s = re.sub(r"Click here to.*$", "", s, flags=re.IGNORECASE | re.MULTILINE)
    s = re.sub(r"Follow us on.*$", "", s, flags=re.IGNORECASE | re.MULTILINE)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def slugify(text_val: str) -> str:
    s = text_val.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s[:140].strip("-")


def tokenize_text(text_val: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", (text_val or "").lower())
    return {w for w in words if w not in STOPWORDS and len(w) > 2}


def jaccard_similarity(tokens1: set[str], tokens2: set[str]) -> float:
    if not tokens1 or not tokens2:
        return 0.0
    intersection = len(tokens1 & tokens2)
    union = len(tokens1 | tokens2)
    return intersection / union if union > 0 else 0.0


def _safe_http_url(value: str) -> str:
    value = html.unescape(str(value or "")).strip()
    try:
        return value if urlparse(value).scheme.lower() in {"http", "https"} else ""
    except ValueError:
        return ""


def is_placeholder_image(url: str | None) -> bool:
    if not url:
        return True
    return bool(PUBLISHER_PLACEHOLDER_REGEX.search(url.strip()))


def _clean_image_url(url: str | None) -> str | None:
    if not url:
        return None
    safe = _safe_http_url(url)
    if not safe or is_placeholder_image(safe) or is_excluded(safe):
        return None
    return safe


def _entry_datetime(entry: object) -> datetime | None:
    parsed = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if not parsed:
        return None
    return datetime.fromtimestamp(calendar.timegm(parsed), tz=timezone.utc)


def _plain_text(value: str) -> str:
    return " ".join(BeautifulSoup(html.unescape(value or ""), "html.parser").get_text(" ").split())


def _clean_title(title: str, source_name: str) -> str:
    cleaned = title
    for suffix in [
        f" - {source_name}", f" | {source_name}", " - The Hindu", " - NDTV",
        " - Times of India", " - Indian Express", " - Livemint", " - Hindustan Times",
        " - News18", " - Financial Express", " - CNN", " - CNN-News18", " - TOI", " - HT",
    ]:
        if cleaned.lower().endswith(suffix.lower()):
            cleaned = cleaned[: -len(suffix)].strip()
    cleaned = re.sub(r"^(?:Live Updates|Breaking|Watch|Photos|Video|Exclusive)\s*[:-]\s*", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def _entry_image(entry: object) -> str:
    for collection_name in ("media_content", "media_thumbnail", "enclosures", "links"):
        for item in getattr(entry, collection_name, []) or []:
            item_type = str(item.get("type", "")).lower()
            candidate = item.get("url") or item.get("href")
            if candidate and ("image" in item_type or collection_name.startswith("media")):
                safe = _safe_http_url(candidate)
                if safe and not is_placeholder_image(safe) and not is_excluded(safe):
                    return safe
    summary = str(getattr(entry, "summary", ""))
    if summary:
        img = BeautifulSoup(summary, "html.parser").find("img", src=True)
        if img:
            safe = _safe_http_url(img.get("src", ""))
            if safe and not is_placeholder_image(safe) and not is_excluded(safe):
                return safe
    return ""


class NewsScraperEngine:
    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(REQUEST_HEADERS)

    def fetch_feed(self, item: tuple[str, str, str], start_time: datetime, end_time: datetime) -> list[SourceArticle]:
        source_name, feed_url, category = item
        if is_excluded(source_name) or is_excluded(feed_url):
            return []

        articles: list[SourceArticle] = []
        try:
            resp = self.session.get(feed_url, timeout=self.timeout)
            if not resp.ok:
                return []
            feed = feedparser.parse(resp.content)
            for entry in getattr(feed, "entries", []):
                link = _safe_http_url(urldefrag(str(getattr(entry, "link", "")).strip()).url)
                if not link or is_excluded(link):
                    continue

                published = _entry_datetime(entry) or datetime.now(timezone.utc)
                if not (start_time <= published <= end_time):
                    continue

                raw_title = _plain_text(getattr(entry, "title", ""))
                if not raw_title or len(raw_title) < 12 or is_excluded(raw_title):
                    continue

                publisher_name = source_name.split(" - ")[0]
                title = _clean_title(raw_title, publisher_name)
                desc = _plain_text(getattr(entry, "summary", ""))
                img = _clean_image_url(_entry_image(entry))

                articles.append(
                    SourceArticle(
                        title=title,
                        url=link,
                        published_at=published,
                        source_name=publisher_name,
                        description=desc,
                        image_url=img,
                        image_caption="Special Report" if img else None,
                        category=category,
                    )
                )
        except Exception:
            pass
        return articles

    def fetch_google_news(self, topic: tuple[str, str, str], start_time: datetime, end_time: datetime) -> list[SourceArticle]:
        topic_name, query_base, category = topic
        after_str = start_time.strftime("%Y-%m-%d")
        query = quote_plus(f"({query_base}) after:{after_str}")
        gnews_url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
        articles: list[SourceArticle] = []
        try:
            resp = self.session.get(gnews_url, timeout=self.timeout)
            if not resp.ok:
                return []
            feed = feedparser.parse(resp.content)
            for entry in getattr(feed, "entries", []):
                published = _entry_datetime(entry) or datetime.now(timezone.utc)
                if not (start_time <= published <= end_time):
                    continue

                link = str(getattr(entry, "link", "")).strip()
                raw_title = _plain_text(getattr(entry, "title", ""))
                source_name = _plain_text(getattr(getattr(entry, "source", {}), "title", "")) or "India News"

                if is_excluded(link) or is_excluded(raw_title) or is_excluded(source_name):
                    continue
                if not link or not raw_title or len(raw_title) < 12:
                    continue

                title = _clean_title(raw_title, source_name)
                desc = _plain_text(getattr(entry, "summary", ""))

                articles.append(
                    SourceArticle(
                        title=title,
                        url=link,
                        published_at=published,
                        source_name=source_name,
                        description=desc,
                        category=category,
                    )
                )
        except Exception:
            pass
        return articles

    def discover_news(self, start_time: datetime, end_time: datetime) -> list[SourceArticle]:
        print(f"[*] Discovering news from {len(TODAYS_FEEDS)} RSS feeds & {len(GOOGLE_NEWS_TOPICS)} Google News topics...", flush=True)
        print(f"[*] Window: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')} -> {end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}", flush=True)
        discovered_map: dict[str, SourceArticle] = {}

        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
            feed_futures = [
                executor.submit(self.fetch_feed, feed_item, start_time, end_time)
                for feed_item in TODAYS_FEEDS
            ]
            gnews_futures = [
                executor.submit(self.fetch_google_news, g_item, start_time, end_time)
                for g_item in GOOGLE_NEWS_TOPICS
            ]

            for future in concurrent.futures.as_completed(feed_futures + gnews_futures):
                try:
                    for art in future.result():
                        if is_excluded(art.url) or is_excluded(art.title) or is_excluded(art.source_name):
                            continue
                        norm_key = re.sub(r"\W+", "", art.title.lower())
                        if norm_key and norm_key not in discovered_map:
                            discovered_map[norm_key] = art
                except Exception:
                    pass

        raw_list = list(discovered_map.values())
        print(f"[*] Raw candidate articles discovered: {len(raw_list)}", flush=True)
        return raw_list

    def enrich(self, article: SourceArticle) -> SourceArticle:
        target_url = article.url
        if is_excluded(target_url):
            return article

        if "news.google.com" in target_url:
            try:
                dec = gnewsdecoder(target_url)
                if dec.get("status") and dec.get("decoded_url"):
                    target_url = str(dec["decoded_url"])
                    article.original_url = target_url
            except Exception:
                pass

        if is_excluded(target_url):
            return article

        try:
            resp = self.session.get(target_url, timeout=12)
            if resp.ok:
                html_text = resp.text
                extracted = trafilatura.extract(
                    html_text,
                    include_comments=False,
                    include_tables=False,
                    favor_precision=True,
                )
                if extracted and len(extracted.strip()) > 300:
                    article.text = " ".join(extracted.split())[:30_000]
                    article.extraction_method = "TRAFILATURA"

                soup = BeautifulSoup(html_text, "html.parser")
                if not article.image_url:
                    og_img = soup.select_one('meta[property="og:image"], meta[name="twitter:image"], meta[property="twitter:image"]')
                    if og_img:
                        cand = _clean_image_url(og_img.get("content", ""))
                        if cand and not is_excluded(cand):
                            article.image_url = cand
                            article.image_caption = "Special Report"
        except Exception:
            pass

        if is_placeholder_image(article.image_url) or is_excluded(article.image_url):
            article.image_url = None
            article.image_caption = None

        return article


class AIRewriterEngine:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.models_to_try = [
            "nvidia/nemotron-3-nano-30b-a3b:free",
            "liquid/lfm-2.5-2.6b:free",
            "google/gemma-4-31b-it:free",
            "google/gemma-4-26b-a4b-it:free",
            "openrouter/free",
        ]

    def _extract_json(self, text_resp: str) -> dict[str, Any]:
        cleaned = text_resp.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            start, end = cleaned.find("{"), cleaned.rfind("}")
            if start >= 0 and end > start:
                return json.loads(cleaned[start : end + 1])
        raise ValueError("Invalid JSON from LLM")

    def rewrite(self, article: SourceArticle) -> RewrittenArticle | None:
        material = clean_editorial_text(article.text or "")
        # Require substantial source material for a long article
        if count_words(material) < 120 and len(material) < 700:
            return None

        user_content = (
            f"Original Headline: {article.title}\n"
            f"Category: {article.category}\n"
            f"Source Text:\n{material[:8000]}\n"
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "AIJournalist Long Article Pipeline",
        }

        for model_name in self.models_to_try:
            body = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": AI_REWRITE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                "temperature": 0.25,
            }

            try:
                resp = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=body,
                    timeout=20,
                )
                if not resp.ok:
                    continue

                res_json = resp.json()
                msg = res_json.get("choices", [{}])[0].get("message", {})
                raw_text = msg.get("content") or ""
                if not raw_text and msg.get("reasoning"):
                    raw_text = msg.get("reasoning")

                if not raw_text or len(raw_text.strip()) < 50:
                    continue

                parsed = self._extract_json(raw_text)
                title = clean_editorial_text(str(parsed.get("title", "")).strip())
                summary = clean_editorial_text(str(parsed.get("summary", "")).strip())
                content_md = clean_editorial_text(str(parsed.get("content_markdown", "")).strip())
                category = str(parsed.get("category", article.category or "General")).strip()
                tags_raw = parsed.get("tags") or ["India", "National", "Special Report", category]
                tags = [str(t).strip() for t in tags_raw if str(t).strip()]

                # STRICT CHECK: Must be a long article (>= 220 words)
                if title and content_md and count_words(content_md) >= 220:
                    return RewrittenArticle(
                        title=title[:200],
                        summary=summary[:600] if summary else content_md[:300],
                        content_markdown=content_md,
                        category=category if category in ["Politics", "Economy", "Technology", "Sports", "General", "World", "Science", "Culture", "Opinion"] else "General",
                        tags=tags[:6],
                    )
            except Exception:
                continue

        # Fallback to deterministic editorial synthesis if source copy is rich enough
        return self.deterministic_long_rewrite(article)

    def deterministic_long_rewrite(self, article: SourceArticle) -> RewrittenArticle | None:
        raw_text = clean_editorial_text(article.text or "")
        if count_words(raw_text) < 150:
            return None

        clean_title = _clean_title(article.title, article.source_name)
        headline = clean_editorial_text(clean_title)
        
        paragraphs = [p.strip() for p in raw_text.split("\n\n") if len(p.strip()) > 50]
        if len(paragraphs) < 3:
            sentences = [s.strip() + "." for s in raw_text.split(". ") if len(s.strip()) > 20]
            if len(sentences) >= 6:
                chunk_size = max(2, len(sentences) // 4)
                paragraphs = [" ".join(sentences[i:i+chunk_size]) for i in range(0, len(sentences), chunk_size)]
            else:
                paragraphs = [raw_text]

        md_sections = []
        md_sections.append(f"## Key Developments\n\n{paragraphs[0]}")
        
        if len(paragraphs) > 1:
            mid = len(paragraphs) // 2
            sec2 = "\n\n".join(paragraphs[1:mid+1])
            md_sections.append(f"## Strategic Context & Background\n\n{sec2}")
            
            if len(paragraphs) > mid + 1:
                sec3 = "\n\n".join(paragraphs[mid+1:])
                md_sections.append(f"## Impact & Future Outlook\n\n{sec3}")

        formatted_md = "\n\n".join(md_sections)
        if count_words(formatted_md) < 200:
            return None

        summary = " ".join(paragraphs[0].split())[:500]
        cat = article.category or "General"
        return RewrittenArticle(
            title=headline[:200],
            summary=summary,
            content_markdown=formatted_md,
            category=cat,
            tags=["India", "News", cat, "Special Report"],
        )


def deduplicate_cross_feed(articles: list[SourceArticle]) -> list[SourceArticle]:
    print(f"[*] Starting cross-feed deduplication on {len(articles)} articles...", flush=True)
    unique_articles: list[SourceArticle] = []
    seen_token_sets: list[tuple[set[str], SourceArticle]] = []

    for art in sorted(articles, key=lambda a: len(a.text or a.description or ""), reverse=True):
        if is_excluded(art.url) or is_excluded(art.title) or is_excluded(art.source_name):
            continue

        tokens = tokenize_text(art.title)
        if not tokens:
            continue

        is_dup = False
        for seen_tokens, _ in seen_token_sets:
            sim = jaccard_similarity(tokens, seen_tokens)
            if sim >= 0.55:
                is_dup = True
                break

        if not is_dup:
            seen_token_sets.append((tokens, art))
            unique_articles.append(art)

    print(f"[+] Unique stories after cross-feed deduplication: {len(unique_articles)} (filtered out {len(articles) - len(unique_articles)} duplicates)", flush=True)
    return unique_articles


async def get_existing_db_articles(session: AsyncSession) -> tuple[set[str], set[str], list[set[str]]]:
    res = await session.execute(
        text("SELECT title, slug FROM articles WHERE published_at >= CURRENT_DATE - INTERVAL '14 days'")
    )
    rows = res.fetchall()
    titles = {r[0].lower().strip() for r in rows if r[0]}
    slugs = {r[1].lower().strip() for r in rows if r[1]}
    token_sets = [tokenize_text(r[0]) for r in rows if r[0]]
    return titles, slugs, token_sets


async def get_valid_author_id(session: AsyncSession) -> int:
    res = await session.execute(
        text("SELECT id FROM users WHERE role IN ('JOURNALIST', 'ADMIN', 'SUPER_ADMIN') ORDER BY id ASC LIMIT 1")
    )
    author_id = res.scalar()
    if not author_id:
        res_any = await session.execute(text("SELECT id FROM users ORDER BY id ASC LIMIT 1"))
        author_id = res_any.scalar()
    if not author_id:
        raise RuntimeError("No users found in database to assign as author.")
    return author_id


async def push_to_database(
    session: AsyncSession,
    rewritten: RewrittenArticle,
    source: SourceArticle,
    author_id: int,
) -> dict[str, Any]:
    # STRICT GUARD: Ensure word count is at least 200 words
    words = count_words(rewritten.content_markdown)
    if words < 200:
        raise ValueError(f"Article '{rewritten.title[:30]}' is too short ({words} words); minimum is 200 words.")

    base_slug = slugify(rewritten.title)
    if not base_slug:
        base_slug = f"news-report-{int(source.published_at.timestamp())}"

    slug = base_slug
    counter = 1
    while True:
        check = await session.execute(text("SELECT 1 FROM articles WHERE slug = :slug LIMIT 1"), {"slug": slug})
        if check.scalar() is None:
            break
        counter += 1
        slug = f"{base_slug}-{counter}"

    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    pub_at = source.published_at.replace(tzinfo=None) if source.published_at else now_utc
    tags_str = ", ".join(rewritten.tags) if rewritten.tags else "India, News, Special Report"

    clean_img = source.image_url if source.image_url and not is_placeholder_image(source.image_url) and not is_excluded(source.image_url) else None
    clean_caption = "Special Report / News Desk" if clean_img else None

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
        "content": rewritten.content_markdown,
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
    return {
        "id": row[0],
        "title": row[1],
        "slug": row[2],
        "status": row[3],
        "category": row[4],
        "words": words,
    }


def process_article_worker(
    scraper: NewsScraperEngine,
    rewriter: AIRewriterEngine,
    article: SourceArticle,
) -> tuple[RewrittenArticle | None, SourceArticle]:
    scraper.enrich(article)
    if count_words(article.text) < 120 and len(article.text or "") < 600:
        return None, article
    rewritten = rewriter.rewrite(article)
    return rewritten, article


async def run_pipeline(start_date_str: str | None = None, max_articles: int = 40, workers: int = 6) -> None:
    configure_console()
    
    if start_date_str:
        start_time = datetime.fromisoformat(start_date_str.replace("Z", "+00:00")).astimezone(timezone.utc)
    else:
        # Default: from August 23, 2026 onwards
        start_time = datetime(2026, 8, 23, 0, 0, 0, tzinfo=timezone.utc)
    
    end_time = datetime.now(timezone.utc)

    print("=" * 75, flush=True)
    print(" LONG-FORM NEWS SCRAPING & AI-REWRITING PIPELINE", flush=True)
    print(" Strict Policy: NO THE HINDU | NO CNN | LONG ARTICLES ONLY (>=200-500 words)", flush=True)
    print(f" Target Window: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')} -> {end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}", flush=True)
    print(f" Max Articles Cap: {max_articles} | Workers: {workers}", flush=True)
    print("=" * 75 + "\n", flush=True)

    scraper = NewsScraperEngine(timeout=15)
    rewriter = AIRewriterEngine(api_key=OPENROUTER_API_KEY)
    ledger = PublicationLedger(BASE_DIR / "publications.sqlite3")

    engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True, pool_recycle=300)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # 1. Discover articles
    raw_discovered = scraper.discover_news(start_time, end_time)

    # 2. Strict Filter: Discard any The Hindu or CNN content
    filtered_articles = [
        art for art in raw_discovered
        if not is_excluded(art.url) and not is_excluded(art.title) and not is_excluded(art.source_name)
    ]
    excluded_discarded = len(raw_discovered) - len(filtered_articles)
    if excluded_discarded > 0:
        print(f"[!] Strictly discarded {excluded_discarded} articles matching exclusions (The Hindu / CNN).", flush=True)

    # 3. Cross-Feed Deduplication
    unique_candidates = deduplicate_cross_feed(filtered_articles)

    # 4. DB Deduplication & Ledger Check
    async with async_session() as session:
        db_titles, db_slugs, db_token_sets = await get_existing_db_articles(session)
        author_id = await get_valid_author_id(session)

    to_process: list[SourceArticle] = []
    skipped_existing = 0

    for art in unique_candidates:
        if ledger.contains(art):
            skipped_existing += 1
            continue

        art_title_lower = art.title.lower().strip()
        art_slug = slugify(art.title)
        if art_title_lower in db_titles or art_slug in db_slugs:
            skipped_existing += 1
            ledger.record(art, 0, "ALREADY_IN_DB")
            continue

        art_tokens = tokenize_text(art.title)
        is_db_dup = False
        for seen_tokens in db_token_sets:
            if jaccard_similarity(art_tokens, seen_tokens) >= 0.55:
                is_db_dup = True
                break

        if is_db_dup:
            skipped_existing += 1
            ledger.record(art, 0, "SIMILAR_TO_DB_ARTICLE")
            continue

        to_process.append(art)
        if len(to_process) >= max_articles * 2:
            break

    print(f"[*] Skipped already existing / duplicate DB stories: {skipped_existing}", flush=True)
    print(f"[+] Fresh candidate stories queued for deep extraction & long rewriting: {len(to_process)}\n", flush=True)

    if not to_process:
        print("No new articles to process. Everything is already up to date in the DB!", flush=True)
        ledger.close()
        await engine.dispose()
        return

    print("-" * 75, flush=True)
    print(f"Enriching, Long-Form AI Rewriting & Ingesting up to {max_articles} Long Articles into PostgreSQL", flush=True)
    print("-" * 75, flush=True)

    inserted = 0
    skipped_short = 0
    failed = 0
    category_counts: dict[str, int] = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_art = {
            executor.submit(process_article_worker, scraper, rewriter, art): art
            for art in to_process
        }

        for idx, future in enumerate(concurrent.futures.as_completed(future_to_art), start=1):
            source_art = future_to_art[future]
            try:
                rewritten_art, enriched_source = future.result()
                if not rewritten_art:
                    skipped_short += 1
                    continue

                words = count_words(rewritten_art.content_markdown)
                if words < 200:
                    skipped_short += 1
                    continue

                # Save to PostgreSQL
                async with async_session() as push_session:
                    pushed = await push_to_database(push_session, rewritten_art, enriched_source, author_id)
                    ledger.record(enriched_source, int(pushed["id"]), str(pushed["status"]))
                    inserted += 1
                    cat = pushed["category"]
                    category_counts[cat] = category_counts.get(cat, 0) + 1
                    
                    print(
                        f"[{inserted}/{max_articles}] SAVED LONG ARTICLE #{pushed['id']} [{cat}] ({pushed['words']} words)"
                        f"\n    Original:  {source_art.title[:70]}"
                        f"\n    Rewritten: {pushed['title'][:70]}"
                        f"\n    Slug:      {pushed['slug']}\n",
                        flush=True,
                    )

                if inserted >= max_articles:
                    print(f"[+] Reached maximum target of {max_articles} long articles. Wrapping up...", flush=True)
                    break

            except Exception as exc:
                failed += 1
                print(f"[{idx}/{len(to_process)}] [!] Skipped/Failed for '{source_art.title[:40]}': {exc}", file=sys.stderr, flush=True)

    ledger.close()
    await engine.dispose()

    print("\n" + "=" * 75, flush=True)
    print(" LONG ARTICLE INGESTION & REWRITING PIPELINE SUMMARY", flush=True)
    print(f" - Raw Discovered: {len(raw_discovered)}", flush=True)
    print(f" - Exclusions (The Hindu / CNN) Discarded: {excluded_discarded}", flush=True)
    print(f" - Cross-Feed Duplicates Removed: {len(filtered_articles) - len(unique_candidates)}", flush=True)
    print(f" - DB Existing / Duplicate Skipped: {skipped_existing}", flush=True)
    print(f" - Short Stubs Filtered Out (<200 words): {skipped_short}", flush=True)
    print(f" - Successfully Rewritten & Pushed to DB (Long): {inserted}", flush=True)
    print(f" - Failures: {failed}", flush=True)
    if category_counts:
        print(" - Categories Breakdown:", flush=True)
        for cat, cnt in sorted(category_counts.items(), key=lambda x: -x[1]):
            print(f"     * {cat}: {cnt}", flush=True)
    print("=" * 75, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape news (excluding The Hindu & CNN), deduplicate, AI-rewrite into long-form reports, and push to DB.")
    parser.add_argument("--start-date", type=str, default="2026-08-23T00:00:00Z", help="Start date in ISO format (e.g. 2026-08-23T00:00:00Z)")
    parser.add_argument("--max", type=int, default=35, help="Maximum long articles to push")
    parser.add_argument("--workers", type=int, default=6, help="Parallel worker threads")
    args = parser.parse_args()

    asyncio.run(run_pipeline(start_date_str=args.start_date, max_articles=args.max, workers=args.workers))
