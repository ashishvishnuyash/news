from __future__ import annotations

import calendar
import concurrent.futures
import html
import re
from datetime import datetime, timezone
from urllib.parse import quote_plus, urldefrag, urlparse

import feedparser
import requests
import trafilatura
from bs4 import BeautifulSoup
from googlenewsdecoder import gnewsdecoder

from models import SourceArticle

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}

JINA_READER_ROOT = "https://r.jina.ai/"

INDIA_FEEDS = [
    # The Hindu
    ("The Hindu - National", "https://www.thehindu.com/news/national/feeder/default.rss", "Politics"),
    ("The Hindu - States", "https://www.thehindu.com/news/states/feeder/default.rss", "General"),
    ("The Hindu - Cities", "https://www.thehindu.com/news/cities/feeder/default.rss", "General"),
    ("The Hindu - Business", "https://www.thehindu.com/business/feeder/default.rss", "Economy"),
    ("The Hindu - Sci-Tech", "https://www.thehindu.com/sci-tech/feeder/default.rss", "Technology"),
    ("The Hindu - Sport", "https://www.thehindu.com/sport/feeder/default.rss", "Sports"),
    ("The Hindu - Opinion", "https://www.thehindu.com/opinion/feeder/default.rss", "Opinion"),
    ("The Hindu - International", "https://www.thehindu.com/news/international/feeder/default.rss", "World"),
    
    # Indian Express
    ("Indian Express - India", "https://indianexpress.com/section/india/feed/", "Politics"),
    ("Indian Express - Business", "https://indianexpress.com/section/business/feed/", "Economy"),
    ("Indian Express - Tech", "https://indianexpress.com/section/technology/feed/", "Technology"),
    ("Indian Express - Sports", "https://indianexpress.com/section/sports/feed/", "Sports"),
    ("Indian Express - Opinion", "https://indianexpress.com/section/opinion/feed/", "Opinion"),
    
    # LiveMint
    ("LiveMint - News", "https://www.livemint.com/rss/news", "Economy"),
    ("LiveMint - Markets", "https://www.livemint.com/rss/markets", "Economy"),
    ("LiveMint - Companies", "https://www.livemint.com/rss/companies", "Economy"),
    
    # Times of India
    ("Times of India - India", "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms", "Politics"),
    ("Times of India - Top Stories", "https://timesofindia.indiatimes.com/rssfeeds/296589292.cms", "General"),
    ("Times of India - Business", "https://timesofindia.indiatimes.com/rssfeeds/1898055.cms", "Economy"),
    ("Times of India - Tech", "https://timesofindia.indiatimes.com/rssfeeds/66949542.cms", "Technology"),
    ("Times of India - Sports", "https://timesofindia.indiatimes.com/rssfeeds/4719148.cms", "Sports"),
    
    # NDTV
    ("NDTV - India", "https://feeds.feedburner.com/ndtvnews-india-news", "Politics"),
    ("NDTV - Top Stories", "https://feeds.feedburner.com/ndtvnews-top-stories", "General"),
    ("NDTV - Business", "https://feeds.feedburner.com/ndtvprofit-latest", "Economy"),
]

GOOGLE_NEWS_TOPICS = [
    ("India Politics & Governance", "India (politics OR government OR parliament OR supreme court)", "Politics"),
    ("India Economy & Markets", "India (economy OR RBI OR GDP OR inflation OR budget OR rupee)", "Economy"),
    ("India Tech & Science", "India (technology OR AI OR ISRO OR semiconductors OR startups)", "Technology"),
    ("India National Affairs", "India (national OR infrastructure OR defense OR education)", "General"),
    ("India Sports & Cricket", "India (cricket OR BCCI OR tournament OR sports)", "Sports"),
]


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


PUBLISHER_PLACEHOLDER_REGEX = re.compile(
    r"("
    r"thehindu\.com/theme/"
    r"|thehindu\.com/.*og[-_]image"
    r"|thehindu\.com/.*default"
    r"|thehindu\.com/static/"
    r"|thehindu\.com/.*logo"
    r"|th-i\.thgim\.com/.*og[-_]image"
    r"|th-i\.thgim\.com/.*default"
    r"|th-i\.thgim\.com/.*logo"
    r"|thehindu-logo"
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


def is_publisher_placeholder_or_logo(url: str | None) -> bool:
    if not url:
        return True
    return bool(PUBLISHER_PLACEHOLDER_REGEX.search(url.strip()))


def _clean_image_url(url: str | None) -> str | None:
    if not url:
        return None
    safe = _safe_http_url(url)
    if not safe or is_publisher_placeholder_or_logo(safe):
        return None
    return safe


def _clean_title(title: str, source_name: str) -> str:
    cleaned = title
    for suffix in [f" - {source_name}", f" | {source_name}", " - The Hindu", " - NDTV", " - Times of India", " - Indian Express", " - Livemint"]:
        if cleaned.lower().endswith(suffix.lower()):
            cleaned = cleaned[: -len(suffix)].strip()
    return cleaned.strip()



class IndiaCompleteNewsSource:
    """Discovers and extracts India-centric news from Aug 13 to present in parallel."""

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(REQUEST_HEADERS)

    def _fetch_publisher_feed(self, item: tuple[str, str, str], start_date: datetime, end_date: datetime) -> list[SourceArticle]:
        source_name, feed_url, category = item
        publisher_name = source_name.split(" - ")[0]
        articles = []
        try:
            resp = self.session.get(feed_url, timeout=self.timeout)
            if not resp.ok:
                return []
            feed = feedparser.parse(resp.content)
            for entry in getattr(feed, "entries", []):
                published = _entry_datetime(entry)
                if published is None:
                    published = datetime.now(timezone.utc)
                if not (start_date <= published <= end_date):
                    continue

                link = _safe_http_url(urldefrag(str(getattr(entry, "link", "")).strip()).url)
                raw_title = _plain_text(getattr(entry, "title", ""))
                if not link or not raw_title or len(raw_title) < 10:
                    continue

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

    def _fetch_google_topic(self, topic: tuple[str, str, str], start_date: datetime, end_date: datetime) -> list[SourceArticle]:
        topic_name, query_base, category = topic
        after_str = start_date.strftime("%Y-%m-%d")
        query = quote_plus(f"({query_base}) after:{after_str}")
        gnews_url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
        articles = []
        try:
            resp = self.session.get(gnews_url, timeout=self.timeout)
            if not resp.ok:
                return []
            feed = feedparser.parse(resp.content)
            for entry in getattr(feed, "entries", []):
                published = _entry_datetime(entry)
                if published is None:
                    published = datetime.now(timezone.utc)
                if not (start_date <= published <= end_date):
                    continue

                link = str(getattr(entry, "link", "")).strip()
                raw_title = _plain_text(getattr(entry, "title", ""))
                if not link or not raw_title:
                    continue

                source_name = _plain_text(getattr(getattr(entry, "source", {}), "title", "")) or "India News"
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

    def discover_all(self, start_date: datetime, end_date: datetime, max_articles: int = 1000) -> list[SourceArticle]:
        """Discover all India news articles in parallel across feeds and Google News."""
        if start_date.tzinfo is None or end_date.tzinfo is None:
            raise ValueError("start_date and end_date must be timezone-aware")

        found: dict[str, SourceArticle] = {}

        print(f"[*] Scanning {len(INDIA_FEEDS)} publisher feeds and {len(GOOGLE_NEWS_TOPICS)} Google News topics in parallel...", flush=True)

        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
            publisher_futures = [
                executor.submit(self._fetch_publisher_feed, feed_item, start_date, end_date)
                for feed_item in INDIA_FEEDS
            ]
            gnews_futures = [
                executor.submit(self._fetch_google_topic, topic_item, start_date, end_date)
                for topic_item in GOOGLE_NEWS_TOPICS
            ]

            for future in concurrent.futures.as_completed(publisher_futures + gnews_futures):
                try:
                    for article in future.result():
                        # Key by simplified title to prevent syndication duplicates
                        norm_key = re.sub(r"\W+", "", article.title.lower())
                        if norm_key and norm_key not in found:
                            found[norm_key] = article
                except Exception:
                    pass

        articles = sorted(found.values(), key=lambda a: a.published_at, reverse=True)
        return articles[:max_articles]

    def enrich(self, article: SourceArticle) -> SourceArticle:
        """Download and extract full article body text and lead image."""
        target_url = article.url

        # Decode Google News URLs if necessary
        if "news.google.com" in target_url:
            try:
                dec = gnewsdecoder(target_url)
                if dec.get("status") and dec.get("decoded_url"):
                    target_url = str(dec["decoded_url"])
                    article.original_url = target_url
            except Exception:
                pass

        # Fetch HTML with browser headers
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
                if extracted and len(extracted.strip()) > 150:
                    article.text = " ".join(extracted.split())[:25_000]
                    article.extraction_method = "TRAFILATURA"

                # Extract Lead Image
                soup = BeautifulSoup(html_text, "html.parser")
                if not article.image_url:
                    og_img = soup.select_one('meta[property="og:image"], meta[name="twitter:image"], meta[property="twitter:image"]')
                    if og_img:
                        candidate_img = _clean_image_url(og_img.get("content", ""))
                        if candidate_img:
                            article.image_url = candidate_img
                            article.image_caption = "Special Report"
        except Exception:
            pass

        # Sanitize image_url and image_caption
        if is_publisher_placeholder_or_logo(article.image_url):
            article.image_url = None
            article.image_caption = None

        # Fallback to description if body is empty or too short
        if len((article.text or "").strip()) < 200 and article.description:
            article.text = article.description

        return article

