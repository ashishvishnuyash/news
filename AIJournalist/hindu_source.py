from __future__ import annotations

import calendar
import html
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urldefrag, urlparse

import feedparser
import requests
import trafilatura
from bs4 import BeautifulSoup

from models import SourceArticle

HINDU_RSS_INDEX = "https://www.thehindu.com/rssfeeds/"
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
JINA_READER_ROOT = "https://r.jina.ai/"

# Category mapping from Hindu RSS section names/paths to system categories
CATEGORY_MAPPING = {
    "national": "India",
    "india": "India",
    "states": "India",
    "cities": "India",
    "international": "World",
    "world": "World",
    "business": "Business",
    "economy": "Business",
    "markets": "Business",
    "industry": "Business",
    "agri-business": "Business",
    "sci-tech": "Technology",
    "science": "Technology",
    "technology": "Technology",
    "gadgets": "Technology",
    "internet": "Technology",
    "sport": "Sports",
    "sports": "Sports",
    "cricket": "Sports",
    "football": "Sports",
    "tennis": "Sports",
    "athletics": "Sports",
    "hockey": "Sports",
    "entertainment": "Entertainment",
    "movies": "Entertainment",
    "cinema": "Entertainment",
    "music": "Entertainment",
    "art": "Entertainment",
    "dance": "Entertainment",
    "theatre": "Entertainment",
    "opinion": "Opinion",
    "editorial": "Opinion",
    "lead": "Opinion",
    "columns": "Opinion",
    "op-ed": "Opinion",
    "life-and-style": "General",
    "fashion": "General",
    "food": "General",
    "fitness": "General",
    "travel": "General",
}


def _entry_datetime(entry: object) -> datetime | None:
    parsed = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if not parsed:
        return None
    return datetime.fromtimestamp(calendar.timegm(parsed), tz=timezone.utc)


def _plain_text(value: str) -> str:
    return " ".join(BeautifulSoup(html.unescape(value or ""), "html.parser").get_text(" ").split())


def _safe_http_url(value: str) -> str:
    value = html.unescape(str(value or "")).strip()
    try:
        return value if urlparse(value).scheme.lower() in {"http", "https"} else ""
    except ValueError:
        return ""


def _entry_image(entry: object) -> str:
    for collection_name in ("media_content", "media_thumbnail", "enclosures", "links"):
        for item in getattr(entry, collection_name, []) or []:
            item_type = str(item.get("type", "")).lower()
            candidate = item.get("url") or item.get("href")
            if candidate and ("image" in item_type or collection_name.startswith("media")):
                safe = _safe_http_url(candidate)
                if safe:
                    return safe
    summary = str(getattr(entry, "summary", ""))
    if summary:
        image = BeautifulSoup(summary, "html.parser").find("img", src=True)
        if image:
            return _safe_http_url(image.get("src", ""))
    return ""


def _map_category(section_name: str, url: str) -> str:
    combined = f"{section_name} {url}".lower()
    for key, mapped in CATEGORY_MAPPING.items():
        if key in combined:
            return mapped
    return "General"


class TheHinduRSSSource:
    """Scrapes authentic Hindu news directly from https://www.thehindu.com/rssfeeds/."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def discover_feed_urls(self) -> list[tuple[str, str]]:
        """Fetch the RSS index page and discover all section RSS feed URLs."""
        try:
            response = requests.get(HINDU_RSS_INDEX, headers=REQUEST_HEADERS, timeout=self.timeout)
            response.raise_for_status()
            matches = re.findall(r'https?://[^\s\'"]+thehindu\.com[^\s\'"]*feeder/default\.rss', response.text)
            feeds: list[tuple[str, str]] = []
            for feed_url in sorted(set(matches)):
                parts = [p for p in feed_url.split("/") if p and p != "feeder" and p != "default.rss" and "thehindu.com" not in p]
                section_name = parts[-1].capitalize() if parts else "News"
                feeds.append((section_name, feed_url))
            if feeds:
                return feeds
        except Exception as exc:
            print(f"Warning: Could not fetch Hindu RSS index ({exc}); using fallback feed list.")

        return [
            ("Home", "https://www.thehindu.com/feeder/default.rss"),
            ("National", "https://www.thehindu.com/news/national/feeder/default.rss"),
            ("International", "https://www.thehindu.com/news/international/feeder/default.rss"),
            ("States", "https://www.thehindu.com/news/states/feeder/default.rss"),
            ("Cities", "https://www.thehindu.com/news/cities/feeder/default.rss"),
            ("Business", "https://www.thehindu.com/business/feeder/default.rss"),
            ("Sport", "https://www.thehindu.com/sport/feeder/default.rss"),
            ("Opinion", "https://www.thehindu.com/opinion/feeder/default.rss"),
            ("Science", "https://www.thehindu.com/sci-tech/science/feeder/default.rss"),
            ("Technology", "https://www.thehindu.com/sci-tech/technology/feeder/default.rss"),
        ]


    def discover(self, start: datetime, end: datetime, max_articles: int = 500) -> list[SourceArticle]:
        """Discover articles from all The Hindu feeds published between start and end."""
        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError("start and end must be timezone-aware")
        if start >= end:
            raise ValueError("start must be earlier than end")

        feeds = self.discover_feed_urls()
        print(f"Scanning {len(feeds)} RSS feeds from The Hindu...")
        found: dict[str, SourceArticle] = {}

        for section_name, feed_url in feeds:
            try:
                response = requests.get(feed_url, headers=REQUEST_HEADERS, timeout=self.timeout)
                if not response.ok:
                    continue
                feed = feedparser.parse(response.content)
                for entry in getattr(feed, "entries", []):
                    published = _entry_datetime(entry)
                    if published is None or not (start <= published <= end):
                        continue
                    link = _safe_http_url(urldefrag(str(getattr(entry, "link", "")).strip()).url)
                    title = _plain_text(getattr(entry, "title", ""))
                    if not link or not title:
                        continue

                    # Check identity
                    identity = link.lower()
                    if identity in found:
                        continue

                    description = _plain_text(getattr(entry, "summary", ""))
                    img = _safe_http_url(image)
                    if any(k in img.lower() for k in ["theme/images", "og-image", "default", "logo", "placeholder", "favicon"]):
                        img = ""

                    article = SourceArticle(
                        title=title,
                        url=link,
                        published_at=published,
                        source_name="The Hindu",
                        description=description,
                        image_url=img or None,
                        image_caption="Special Report" if img else None,
                        extraction_method="RSS",
                        category=_map_category(section_name, link),
                    )
                    found[identity] = article

            except Exception as exc:
                print(f"Skipping feed {feed_url} due to error: {exc}")

        articles = sorted(found.values(), key=lambda item: item.published_at, reverse=True)
        return articles[:max_articles]

    def enrich(self, article: SourceArticle) -> SourceArticle:
        """Extract full reporting body text directly from The Hindu article URL."""
        try:
            response = requests.get(article.url, headers=REQUEST_HEADERS, timeout=self.timeout)
            if response.ok:
                downloaded = response.text
                extracted = trafilatura.extract(
                    downloaded,
                    include_comments=False,
                    include_tables=False,
                    favor_precision=True,
                )
                if extracted and len(extracted.strip()) > 100:
                    article.text = " ".join(extracted.split())[:25_000]
                    article.extraction_method = "DIRECT"

                soup = BeautifulSoup(downloaded, "html.parser")
                if not article.image_url:
                    image = soup.select_one('meta[property="og:image"], meta[name="twitter:image"]')
                    if image:
                        cand = _safe_http_url(image.get("content", ""))
                        if not any(k in cand.lower() for k in ["theme/images", "og-image", "default", "logo", "placeholder", "favicon"]):
                            article.image_url = cand
                            article.image_caption = "Special Report"
        except requests.RequestException:
            pass

        # If direct extraction returned short text, try Jina Reader fallback
        if len(article.text.strip()) < 300:
            try:
                reader_url = f"{JINA_READER_ROOT}{article.url}"
                res = requests.get(reader_url, headers={**REQUEST_HEADERS, "Accept": "text/plain"}, timeout=45)
                if res.ok:
                    raw = res.text.strip()
                    marker = "Markdown Content:"
                    content = raw.split(marker, 1)[1].strip() if marker in raw else raw
                    content = re.sub(r"!\[[^\]]*\]\(https?://[^)]+\)\s*", "", content)
                    if len(content.strip()) > len(article.text.strip()):
                        article.text = content[:25_000]
                        article.extraction_method = "JINA_READER"
            except requests.RequestException:
                pass

        # If no full body text could be scraped, use description as fallback
        if not article.text.strip() and article.description:
            article.text = article.description

        if article.image_url and any(k in article.image_url.lower() for k in ["theme/images", "og-image", "default", "logo", "placeholder", "favicon"]):
            article.image_url = None
            article.image_caption = None

        return article
