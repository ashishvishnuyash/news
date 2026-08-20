from __future__ import annotations

import calendar
import html
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus, urldefrag, urlparse

import feedparser
import requests
import trafilatura
from bs4 import BeautifulSoup
from googlenewsdecoder import gnewsdecoder

from models import SourceArticle
from hindu_source import TheHinduRSSSource



GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"
DEFAULT_QUERIES = (
    "India (politics OR government OR economy OR business)",
    "India (technology OR science OR health OR environment)",
    "India (society OR culture OR sports OR education)",
)
INDIA_PUBLISHER_FEEDS = (
    ("NDTV", "https://feeds.feedburner.com/ndtvnews-india-news"),
    ("Times of India", "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms"),
)
REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AIJournalist/1.0; editorial aggregation)"}
JINA_READER_ROOT = "https://r.jina.ai/"

# Used after extraction so a broad search match cannot turn into unrelated world news.
INDIA_TERMS = re.compile(
    r"\b(?:india|indian|new delhi|delhi|mumbai|kolkata|chennai|bengaluru|bangalore|"
    r"hyderabad|ahmedabad|pune|jaipur|lucknow|srinagar|guwahati|bhubaneswar|"
    r"andhra pradesh|arunachal pradesh|assam|bihar|chhattisgarh|goa|gujarat|haryana|"
    r"himachal pradesh|jharkhand|karnataka|kerala|madhya pradesh|maharashtra|manipur|"
    r"meghalaya|mizoram|nagaland|odisha|punjab|rajasthan|sikkim|tamil nadu|telangana|"
    r"uttar pradesh|uttarakhand|west bengal|jammu and kashmir|ladakh|lok sabha|rajya sabha|"
    r"supreme court of india|reserve bank of india|rbi|isro|sebi|niti aayog)\b",
    flags=re.IGNORECASE,
)


def _entry_datetime(entry: object) -> datetime | None:
    parsed = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if not parsed:
        return None
    return datetime.fromtimestamp(calendar.timegm(parsed), tz=timezone.utc)


def _plain_text(value: str) -> str:
    return " ".join(BeautifulSoup(html.unescape(value or ""), "html.parser").get_text(" ").split())


def _clean_title(title: str, source_name: str) -> str:
    suffix = f" - {source_name}" if source_name else ""
    if suffix and title.lower().endswith(suffix.lower()):
        return title[: -len(suffix)].strip()
    return title.strip()


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


def _entry_description(entry: object) -> str:
    values = [getattr(entry, "summary", "")]
    for content in getattr(entry, "content", []) or []:
        values.append(content.get("value", ""))
    plain_values = [_plain_text(value) for value in values if value]
    return " ".join(dict.fromkeys(value for value in plain_values if value))


def _jina_reader_extract(url: str, timeout: int) -> tuple[str, str]:
    """Return article Markdown and a lead image through Jina Reader."""
    reader_url = f"{JINA_READER_ROOT}{url}"
    response = requests.get(
        reader_url,
        timeout=max(timeout, 45),
        headers={**REQUEST_HEADERS, "Accept": "text/plain"},
    )
    response.raise_for_status()
    raw = response.text.strip()
    marker = "Markdown Content:"
    content = raw.split(marker, 1)[1].strip() if marker in raw else raw
    image_match = re.search(r"!\[[^\]]*\]\((https?://[^)]+)\)", content)
    image_url = _safe_http_url(image_match.group(1)) if image_match else ""
    # Image markup adds no reporting context and can contain very long transform URLs.
    content = re.sub(r"!\[[^\]]*\]\(https?://[^)]+\)\s*", "", content)
    return content[:20_000], image_url


def is_india_focused(article: SourceArticle) -> bool:
    material = " ".join((article.title, article.description, article.text))
    return INDIA_TERMS.search(material) is not None


class GoogleNewsRSSSource:
    """Key-free Google News RSS discovery, constrained to Indian editions and terms."""

    def __init__(self, timeout: int = 30, queries: tuple[str, ...] = DEFAULT_QUERIES):
        self.timeout = timeout
        self.queries = queries

    def discover(self, start: datetime, end: datetime, limit: int) -> list[SourceArticle]:
        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError("start and end must be timezone-aware")
        if start >= end:
            raise ValueError("start must be earlier than end")

        # Google date operators work by calendar day. Exact time filtering happens below.
        after = start.date().isoformat()
        before = (end.date() + timedelta(days=1)).isoformat()
        found: dict[str, SourceArticle] = {}

        for topic in self.queries:
            query = quote_plus(f"({topic}) after:{after} before:{before}")
            url = f"{GOOGLE_NEWS_RSS}?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
            response = requests.get(
                url,
                timeout=self.timeout,
                headers=REQUEST_HEADERS,
            )
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            if getattr(feed, "bozo", False) and not getattr(feed, "entries", []):
                raise RuntimeError(f"Could not parse Google News RSS: {feed.bozo_exception}")

            for entry in feed.entries:
                published = _entry_datetime(entry)
                if published is None or not (start <= published <= end):
                    continue
                source_name = _plain_text(getattr(getattr(entry, "source", {}), "title", ""))
                link = str(getattr(entry, "link", "")).strip()
                if not link:
                    continue
                article = SourceArticle(
                    title=_clean_title(_plain_text(getattr(entry, "title", "")), source_name),
                    url=link,
                    published_at=published,
                    source_name=source_name or "Google News source",
                    description=_plain_text(getattr(entry, "summary", "")),
                )
                # A stable URL wins; title fallback catches repeated syndicated entries.
                key = re.sub(r"\W+", "", article.title.lower()) or article.identity
                found.setdefault(key, article)

        return sorted(found.values(), key=lambda item: item.published_at, reverse=True)[:limit]

    def enrich(self, article: SourceArticle) -> SourceArticle:
        """Best-effort extraction. RSS text remains available when a publisher blocks access."""
        try:
            target_url = article.url
            if "news.google.com/" in target_url:
                decoded = gnewsdecoder(target_url)
                if decoded.get("status") and decoded.get("decoded_url"):
                    target_url = str(decoded["decoded_url"])
                    article.original_url = target_url
            downloaded = trafilatura.fetch_url(target_url)
            if downloaded:
                extracted = trafilatura.extract(
                    downloaded,
                    include_comments=False,
                    include_tables=False,
                    favor_precision=True,
                )
                if extracted:
                    article.text = " ".join(extracted.split())[:20_000]
                    article.extraction_method = "DIRECT"
                soup = BeautifulSoup(downloaded, "html.parser")
                if not article.image_url:
                    image = soup.select_one('meta[property="og:image"], meta[name="twitter:image"]')
                    if image:
                        article.image_url = _safe_http_url(image.get("content", ""))
        except Exception:
            # Individual publisher failures should not abort the whole batch.
            pass
        return article


class IndiaPublisherRSSSource:
    """India feeds published by NDTV and The Times of India."""

    def __init__(self, timeout: int = 30, feeds: tuple[tuple[str, str], ...] = INDIA_PUBLISHER_FEEDS):
        self.timeout = timeout
        self.feeds = feeds

    def discover(self, start: datetime, end: datetime, limit: int = 200) -> list[SourceArticle]:
        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError("start and end must be timezone-aware")
        if start >= end:
            raise ValueError("start must be earlier than end")
        found: dict[str, SourceArticle] = {}

        for publisher, feed_url in self.feeds:
            response = requests.get(feed_url, timeout=self.timeout, headers=REQUEST_HEADERS)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            if getattr(feed, "bozo", False) and not getattr(feed, "entries", []):
                raise RuntimeError(f"Could not parse {publisher} RSS: {feed.bozo_exception}")
            for entry in feed.entries:
                published = _entry_datetime(entry)
                if published is None or not (start <= published <= end):
                    continue
                link = _safe_http_url(urldefrag(str(getattr(entry, "link", "")).strip()).url)
                title = _plain_text(getattr(entry, "title", ""))
                if not link or not title:
                    continue
                article = SourceArticle(
                    title=_clean_title(title, publisher),
                    url=link,
                    published_at=published,
                    source_name=publisher,
                    description=_entry_description(entry),
                    image_url=_entry_image(entry),
                    image_caption=f"Source image via {publisher}; verify reuse rights before publication",
                )
                found.setdefault(article.identity, article)

        return sorted(found.values(), key=lambda item: item.published_at, reverse=True)[:limit]

    def enrich(self, article: SourceArticle) -> SourceArticle:
        """Extract the linked report and Open Graph image when the publisher permits it."""
        try:
            response = requests.get(article.url, timeout=self.timeout, headers=REQUEST_HEADERS)
            if response.ok:
                downloaded = response.text
                extracted = trafilatura.extract(
                    downloaded,
                    include_comments=False,
                    include_tables=False,
                    favor_precision=True,
                )
                if extracted:
                    article.text = " ".join(extracted.split())[:20_000]
                    article.extraction_method = "DIRECT"
                soup = BeautifulSoup(downloaded, "html.parser")
                if not article.image_url:
                    image = soup.select_one('meta[property="og:image"], meta[name="twitter:image"]')
                    if image:
                        article.image_url = _safe_http_url(image.get("content", ""))
        except requests.RequestException:
            pass
        if len(article.text.strip()) < 600:
            try:
                reader_text, reader_image = _jina_reader_extract(article.url, self.timeout)
                if len(reader_text.strip()) > len(article.text.strip()):
                    article.text = reader_text
                    article.extraction_method = "JINA_READER"
                if not article.image_url and reader_image:
                    article.image_url = reader_image
            except requests.RequestException:
                pass
        return article
