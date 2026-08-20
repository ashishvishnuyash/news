from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from types import SimpleNamespace


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import parse_local_datetime
from models import RewrittenArticle, SourceArticle
from publisher import PublicationLedger, SiteClient
from rewriter import OpenRouterRewriter, _extract_json, build_source_fallback
from sources import IndiaPublisherRSSSource, is_india_focused
from dashboard import ArticlePreview, ResearchJob, ResearchRequest, app, manager, resolve_range
from fastapi.testclient import TestClient


def test_parse_local_datetime_accepts_date_and_minute():
    assert parse_local_datetime("2026-08-05", timezone.utc) == datetime(2026, 8, 5, tzinfo=timezone.utc)
    assert parse_local_datetime("2026-08-05 14:30", timezone.utc) == datetime(2026, 8, 5, 14, 30, tzinfo=timezone.utc)


def test_extract_json_accepts_fenced_response():
    result = _extract_json('```json\n{"title": "A story"}\n```')
    assert result == {"title": "A story"}


def test_extract_json_finds_object_around_model_chatter():
    result = _extract_json('Result follows: {"title": "A story"} done')
    assert result["title"] == "A story"


def test_india_focus_accepts_indian_locations_and_rejects_unrelated_world_story():
    timestamp = datetime(2026, 8, 5, tzinfo=timezone.utc)
    indian = SourceArticle("Ahmedabad prepares for games", "https://example.test/1", timestamp, "Example")
    unrelated = SourceArticle("Brazil announces soil programme", "https://example.test/2", timestamp, "Example")
    assert is_india_focused(indian)
    assert not is_india_focused(unrelated)


def test_openrouter_rewriter_builds_site_article():
    source = SourceArticle(
        "India announces a detailed public programme",
        "https://example.test/story",
        datetime(2026, 8, 5, tzinfo=timezone.utc),
        "Example News",
        text="India announced a public programme with documented details. " * 20,
    )
    content = "## Detailed report\n\n" + ("The programme details were set out clearly for readers across India. " * 55)
    response_data = {
        "title": "India announces public programme",
        "summary": "The programme was announced with detailed provisions relevant to readers across India. The source outlines its stated purpose, location, and review period without supplying budgets or participation totals. The report therefore focuses on the documented announcement and avoids unsupported claims about outcomes.",
        "content_markdown": content,
        "category": "Politics",
        "tags": ["India", "policy", "programme"],
    }
    seen = {}

    class FakeChat:
        def send(self, **kwargs):
            seen.update(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(response_data)))]
            )

    fake_client = SimpleNamespace(chat=FakeChat())
    result = OpenRouterRewriter("test-key", client=fake_client).rewrite(source, ["Politics", "Economy"])
    assert result.category == "Politics"
    assert result.tags == ["India", "policy", "programme"]
    assert seen["model"] == "openrouter/free"


def test_openrouter_rewriter_accepts_substantial_plain_markdown_response():
    source = SourceArticle(
        "India policy report",
        "https://example.test/story",
        datetime(2026, 8, 5, tzinfo=timezone.utc),
        "Example News",
        description="A detailed India policy report and its documented context. " * 12,
    )
    markdown_content = "## Report\n\n" + ("Documented details were reorganised for readers in India. " * 45)
    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            send=lambda **kwargs: SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=markdown_content))]
            )
        )
    )
    result = OpenRouterRewriter("test-key", client=fake_client).rewrite(source)
    assert result.title == source.title
    assert result.content_markdown == markdown_content.strip()
    assert len(result.summary) >= 100


def test_ledger_deduplicates_same_title_from_a_changed_url(tmp_path):
    timestamp = datetime(2026, 8, 5, tzinfo=timezone.utc)
    first = SourceArticle("Same headline", "https://example.test/old", timestamp, "Example")
    second = SourceArticle("Same headline", "https://example.test/new", timestamp, "Example")
    ledger = PublicationLedger(tmp_path / "ledger.sqlite3")
    try:
        ledger.record(first, 42, "DRAFT")
        assert ledger.contains(second)
    finally:
        ledger.close()


def test_dashboard_resolves_complete_indian_date():
    request = ResearchRequest(range_type="date", selected_date="2026-08-05", max_articles=3)
    start, end = resolve_range(request, "Asia/Kolkata")
    assert start.isoformat() == "2026-08-05T00:00:00+05:30"
    assert end.isoformat() == "2026-08-05T23:59:59.999999+05:30"


def test_dashboard_resolves_datetime_local_interval():
    request = ResearchRequest(
        range_type="interval",
        start="2026-08-05T09:15",
        end="2026-08-05T17:45",
        max_articles=3,
    )
    start, end = resolve_range(request, "Asia/Kolkata")
    assert start.hour == 9 and start.minute == 15
    assert end.hour == 17 and end.minute == 45


def test_markdown_is_converted_to_html_only_for_site_payload():
    article = RewrittenArticle(
        title="A detailed Indian report",
        summary="A sufficiently detailed summary for the publication workflow.",
        content_markdown="## Background\n\nA **documented** development.",
        category="Politics",
        tags=["India"],
    )
    payload = article.site_payload()
    assert "<h2>Background</h2>" in payload["content"]
    assert "<strong>documented</strong>" in payload["content"]


def test_site_client_normalizes_api_suffix():
    assert SiteClient("http://localhost:8000", "u", "p").api_root == "http://localhost:8000/api"
    assert SiteClient("http://localhost:8000/api", "u", "p").api_root == "http://localhost:8000/api"


def test_source_fallback_contains_extracted_copy_and_is_marked_as_draft_material():
    source = SourceArticle(
        "Delhi source report",
        "https://example.test/report",
        datetime(2026, 8, 5, tzinfo=timezone.utc),
        "Example Publisher",
        text="documented source wording " * 300,
    )
    fallback = build_source_fallback(source)
    assert "source fallback" in fallback.tags
    assert "Editorial note" in fallback.content_markdown
    assert "Extracted source copy" in fallback.content_markdown
    assert len(fallback.content_markdown.split()) > 300
    assert source.url in fallback.content_markdown


def test_publisher_rss_discovers_feed_image(monkeypatch):
    rss = b'''<?xml version="1.0"?><rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/"><channel>
      <item><title>Delhi policy report</title><link>https://example.test/delhi</link>
      <pubDate>Wed, 05 Aug 2026 10:00:00 GMT</pubDate><description>India policy details.</description>
      <media:content url="https://images.example.test/lead.jpg" type="image/jpeg" /></item>
    </channel></rss>'''

    class FakeResponse:
        content = rss

        def raise_for_status(self):
            return None

    monkeypatch.setattr("sources.requests.get", lambda *args, **kwargs: FakeResponse())
    source = IndiaPublisherRSSSource(feeds=(("NDTV", "https://example.test/feed"),))
    items = source.discover(
        datetime(2026, 8, 5, 9, tzinfo=timezone.utc),
        datetime(2026, 8, 5, 11, tzinfo=timezone.utc),
    )
    assert len(items) == 1
    assert items[0].source_name == "NDTV"
    assert items[0].image_url == "https://images.example.test/lead.jpg"


def test_site_post_attaches_source_image_and_marks_fallback(monkeypatch):
    source = SourceArticle(
        "Delhi source report",
        "https://example.test/report",
        datetime(2026, 8, 5, tzinfo=timezone.utc),
        "NDTV",
        description="A documented India report with enough text for a source summary.",
        image_url="https://images.example.test/lead.jpg",
        image_caption="Source image via NDTV; verify reuse rights before publication",
    )
    article = build_source_fallback(source)
    captured = {}

    class FakeResponse:
        ok = True

        def json(self):
            return {"id": 7, "status": "DRAFT"}

    client = SiteClient("http://localhost:8000", "journalist", "password")

    def fake_post(url, **kwargs):
        captured.update(kwargs["json"])
        return FakeResponse()

    monkeypatch.setattr(client.session, "post", fake_post)
    client.post(article, source, "DRAFT")
    assert captured["image_url"] == source.image_url
    assert captured["image_caption"].startswith("Source image via NDTV")
    assert "attributed extracted copy" in captured["content"]


def test_markdown_download_endpoint_uses_safe_filename():
    source = SourceArticle(
        "Delhi report",
        "https://example.test/report",
        datetime(2026, 8, 5, tzinfo=timezone.utc),
        "NDTV",
    )
    article = RewrittenArticle(
        title="India: A Detailed Report!",
        summary="A detailed summary suitable for the newsroom download test.",
        content_markdown="## Report\n\nMarkdown copy.",
        category="Politics",
        tags=["India"],
    )
    job = ResearchJob(
        id="download-test",
        start=datetime(2026, 8, 5, tzinfo=timezone.utc),
        end=datetime(2026, 8, 6, tzinfo=timezone.utc),
        max_articles=1,
        previews=[ArticlePreview("preview-test", source, article)],
    )
    with manager.lock:
        manager.jobs[job.id] = job
    try:
        response = TestClient(app).get(f"/api/jobs/{job.id}/previews/preview-test/markdown")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/markdown")
        assert 'filename="india-a-detailed-report.md"' in response.headers["content-disposition"]
    finally:
        with manager.lock:
            manager.jobs.pop(job.id, None)
