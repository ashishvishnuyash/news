from __future__ import annotations

import re
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

from config import Settings
from models import RewrittenArticle, SourceArticle
from publisher import PublicationLedger, SiteClient
from rewriter import OpenRouterRewriter, build_source_fallback
from sources import IndiaPublisherRSSSource


BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "webui"
LEDGER_PATH = BASE_DIR / "publications.sqlite3"


class ResearchRequest(BaseModel):
    range_type: Literal["date", "interval"] = "date"
    selected_date: str | None = None
    start: str | None = None
    end: str | None = None
    max_articles: int = Field(default=5, ge=1, le=25)

    @model_validator(mode="after")
    def validate_range_fields(self):
        if self.range_type == "date" and not self.selected_date:
            raise ValueError("A date is required")
        if self.range_type == "interval" and (not self.start or not self.end):
            raise ValueError("Start and end times are required")
        return self


class PublishRequest(BaseModel):
    preview_ids: list[str] = Field(min_length=1, max_length=25)
    status: Literal["DRAFT", "SUBMITTED", "PUBLISHED"] = "DRAFT"


@dataclass(slots=True)
class ArticlePreview:
    id: str
    source: SourceArticle
    article: RewrittenArticle
    rewrite_mode: str = "AI_REWRITE"
    state: str = "READY"
    site_article_id: int | None = None
    site_status: str | None = None
    error: str | None = None

    def public(self) -> dict:
        return {
            "id": self.id,
            "state": self.state,
            "site_article_id": self.site_article_id,
            "site_status": self.site_status,
            "error": self.error,
            "rewrite_mode": self.rewrite_mode,
            "source": {
                "title": self.source.title,
                "url": self.source.attribution_url,
                "publisher": self.source.source_name,
                "published_at": self.source.published_at.isoformat(),
                "image_url": self.source.image_url,
                "image_caption": self.source.image_caption,
                "extraction_method": self.source.extraction_method,
            },
            "article": {
                "title": self.article.title,
                "summary": self.article.summary,
                "content_markdown": self.article.content_markdown,
                "category": self.article.category,
                "tags": self.article.tags,
            },
        }


@dataclass(slots=True)
class ResearchJob:
    id: str
    start: datetime
    end: datetime
    max_articles: int
    state: str = "QUEUED"
    stage: str = "Waiting to start"
    current: int = 0
    total: int = 0
    skipped: int = 0
    failed: int = 0
    error: str | None = None
    cancel_requested: bool = False
    previews: list[ArticlePreview] = field(default_factory=list)
    logs: list[dict[str, str]] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def public(self) -> dict:
        return {
            "id": self.id,
            "state": self.state,
            "stage": self.stage,
            "current": self.current,
            "total": self.total,
            "skipped": self.skipped,
            "failed": self.failed,
            "error": self.error,
            "cancel_requested": self.cancel_requested,
            "created_at": self.created_at.isoformat(),
            "range": {"start": self.start.isoformat(), "end": self.end.isoformat()},
            "previews": [preview.public() for preview in self.previews],
            "logs": list(self.logs[-200:]),
        }


class JobManager:
    def __init__(self):
        self.jobs: dict[str, ResearchJob] = {}
        self.lock = threading.RLock()
        # A single worker avoids free-model rate spikes and SQLite contention.
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ai-journalist")

    def create(self, start: datetime, end: datetime, maximum: int) -> ResearchJob:
        job = ResearchJob(uuid.uuid4().hex, start, end, maximum)
        with self.lock:
            self.jobs[job.id] = job
            # Bound in-memory history without touching publication records.
            if len(self.jobs) > 20:
                removable = [key for key, item in self.jobs.items() if item.state not in {"QUEUED", "RESEARCHING", "PUBLISHING"}]
                for key in removable[: len(self.jobs) - 20]:
                    self.jobs.pop(key, None)
        self.executor.submit(self._research, job.id)
        return job

    def get(self, job_id: str) -> ResearchJob:
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                raise KeyError(job_id)
            return job

    def snapshot(self, job_id: str) -> dict:
        with self.lock:
            return self.get(job_id).public()

    def log(self, job: ResearchJob, message: str) -> None:
        with self.lock:
            job.logs.append({
                "time": datetime.now(timezone.utc).isoformat(),
                "message": message,
            })

    def cancel(self, job_id: str) -> ResearchJob:
        with self.lock:
            job = self.get(job_id)
            if job.state in {"QUEUED", "RESEARCHING", "PUBLISHING"}:
                job.cancel_requested = True
                self.log(job, "Cancellation requested; the current operation will finish safely.")
            return job

    def publish(self, job_id: str, preview_ids: list[str], status: str) -> ResearchJob:
        with self.lock:
            job = self.get(job_id)
            if job.state not in {"READY", "COMPLETE", "CANCELLED"}:
                raise ValueError("This job is not ready to publish")
            ready_ids = {item.id for item in job.previews if item.state == "READY"}
            selected = list(dict.fromkeys(preview_ids))
            if not selected or any(item not in ready_ids for item in selected):
                raise ValueError("Choose one or more unpublished preview articles")
            job.state = "PUBLISHING"
            job.stage = f"Publishing {len(selected)} article(s) as {status}"
            job.error = None
            job.cancel_requested = False
        self.executor.submit(self._publish, job_id, selected, status)
        return job

    def _research(self, job_id: str) -> None:
        job = self.get(job_id)
        ledger: PublicationLedger | None = None
        try:
            with self.lock:
                if job.cancel_requested:
                    job.state = "CANCELLED"
                    job.stage = "Research cancelled"
                    self.log(job, "Cancelled before research began.")
                    return
            settings = Settings()
            if not settings.openrouter_api_key:
                raise ValueError("OPENROUTER_API_KEY is not configured")
            with self.lock:
                job.state = "RESEARCHING"
                job.stage = "Discovering India-focused reports"
            self.log(job, f"Searching {job.start.isoformat()} to {job.end.isoformat()}.")

            source_client = IndiaPublisherRSSSource(timeout=settings.timeout)
            candidates = source_client.discover(job.start, job.end, 200)
            with self.lock:
                job.total = len(candidates) + min(len(candidates), job.max_articles)
            self.log(job, f"Found {len(candidates)} NDTV/Times of India RSS report(s).")
            if not candidates:
                with self.lock:
                    job.state = "COMPLETE"
                    job.stage = "No matching reports found"
                return

            site = SiteClient(settings.site_api_url, settings.site_username, settings.site_password, settings.timeout)
            categories = site.categories()
            rewriter = OpenRouterRewriter(
                settings.openrouter_api_key,
                settings.openrouter_model,
                settings.timeout,
                settings.openrouter_site_url,
                settings.openrouter_app_name,
            )
            ledger = PublicationLedger(LEDGER_PATH)
            extracted: list[SourceArticle] = []

            for position, candidate in enumerate(candidates, start=1):
                with self.lock:
                    job.current = position
                    if job.cancel_requested:
                        job.state = "CANCELLED"
                        job.stage = "Research cancelled"
                        self.log(job, "Stopped before processing the next report.")
                        return
                    job.stage = f"Extracting source report {position} of {len(candidates)}"

                if ledger.contains(candidate):
                    with self.lock:
                        job.skipped += 1
                    self.log(job, f"Duplicate skipped: {candidate.title}")
                    continue

                self.log(job, f"Reading: {candidate.title}")
                source_client.enrich(candidate)
                self.log(
                    job,
                    f"Extracted {len((candidate.text or candidate.description).strip()):,} characters via {candidate.extraction_method}.",
                )
                extracted.append(candidate)

            to_rewrite = extracted[: job.max_articles]
            with self.lock:
                job.total = len(candidates) + len(to_rewrite)
            self.log(job, f"Extraction phase complete; sending {len(to_rewrite)} report(s) for rewriting.")

            for rewrite_position, candidate in enumerate(to_rewrite, start=1):
                with self.lock:
                    job.current = len(candidates) + rewrite_position
                    if job.cancel_requested:
                        job.state = "CANCELLED"
                        job.stage = "Research cancelled"
                        self.log(job, "Stopped before the next AI rewrite.")
                        return
                    job.stage = f"Rewriting report {rewrite_position} of {len(to_rewrite)}"

                rewrite_mode = "AI_REWRITE"
                try:
                    rewritten = rewriter.rewrite(candidate, categories or None)
                except Exception as exc:
                    rewritten = build_source_fallback(candidate, categories or None)
                    rewrite_mode = "SOURCE_FALLBACK"
                    with self.lock:
                        job.failed += 1
                    self.log(job, f"AI rewrite failed; created an attributed source-excerpt draft: {exc}")

                preview = ArticlePreview(uuid.uuid4().hex, candidate, rewritten, rewrite_mode)
                with self.lock:
                    job.previews.append(preview)
                self.log(job, f"Preview ready: {rewritten.title}")

            with self.lock:
                if job.cancel_requested:
                    job.state = "CANCELLED"
                    job.stage = "Research cancelled"
                elif job.previews:
                    job.state = "READY"
                    job.stage = f"{len(job.previews)} article preview(s) ready"
                else:
                    job.state = "COMPLETE"
                    job.stage = "No publishable previews were produced"
        except Exception as exc:
            with self.lock:
                job.state = "FAILED"
                job.stage = "Research failed"
                job.error = str(exc)
            self.log(job, f"Research failed: {exc}")
        finally:
            if ledger:
                ledger.close()

    def _publish(self, job_id: str, preview_ids: list[str], status: str) -> None:
        job = self.get(job_id)
        ledger: PublicationLedger | None = None
        try:
            settings = Settings()
            site = SiteClient(settings.site_api_url, settings.site_username, settings.site_password, settings.timeout)
            user = site.login()
            role = str(user["role"]).upper()
            selected = [item for item in job.previews if item.id in preview_ids]
            if role not in {"JOURNALIST", "ADMIN", "SUPER_ADMIN"}:
                raise ValueError(f"Site role {role} cannot create articles")
            if status == "PUBLISHED" and role not in {"ADMIN", "SUPER_ADMIN"} and any(
                item.rewrite_mode == "AI_REWRITE" for item in selected
            ):
                raise ValueError("Direct publishing requires an ADMIN or SUPER_ADMIN account")
            self.log(job, f"Authenticated on the site as {user['username']} ({role}).")
            ledger = PublicationLedger(LEDGER_PATH)

            for index, preview in enumerate(selected, start=1):
                with self.lock:
                    if job.cancel_requested:
                        job.state = "READY"
                        job.stage = "Publishing stopped"
                        self.log(job, "Stopped before publishing the next article.")
                        return
                    job.stage = f"Publishing article {index} of {len(selected)}"
                    preview.state = "PUBLISHING"
                try:
                    if ledger.contains(preview.source):
                        with self.lock:
                            preview.state = "SKIPPED"
                            preview.error = "This source is already in the publication ledger"
                            job.skipped += 1
                        self.log(job, f"Duplicate blocked: {preview.article.title}")
                        continue
                    actual_status = "DRAFT" if preview.rewrite_mode == "SOURCE_FALLBACK" else status
                    if actual_status != status:
                        self.log(job, f"Safety fallback: {preview.article.title} will be posted as DRAFT only.")
                    result = site.post(preview.article, preview.source, actual_status)
                    ledger.record(preview.source, int(result["id"]), str(result["status"]))
                    with self.lock:
                        preview.state = "POSTED"
                        preview.site_article_id = int(result["id"])
                        preview.site_status = str(result["status"])
                    self.log(job, f"Posted article #{result['id']}: {preview.article.title}")
                except Exception as exc:
                    with self.lock:
                        preview.state = "FAILED"
                        preview.error = str(exc)
                        job.failed += 1
                    self.log(job, f"Publish failed for {preview.article.title}: {exc}")

            with self.lock:
                remaining = any(item.state == "READY" for item in job.previews)
                job.state = "READY" if remaining else "COMPLETE"
                job.stage = "Publishing finished"
        except Exception as exc:
            with self.lock:
                job.state = "READY"
                job.stage = "Publishing could not start"
                job.error = str(exc)
            self.log(job, f"Publishing could not start: {exc}")
        finally:
            if ledger:
                ledger.close()


def _parse_local(value: str, zone: ZoneInfo) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Use a valid date and time") from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=zone)
    return parsed.astimezone(zone)


def resolve_range(request: ResearchRequest, timezone_name: str) -> tuple[datetime, datetime]:
    zone = ZoneInfo(timezone_name)
    if request.range_type == "date":
        try:
            start = datetime.strptime(request.selected_date or "", "%Y-%m-%d").replace(tzinfo=zone)
        except ValueError as exc:
            raise ValueError("Date must use YYYY-MM-DD") from exc
        end = start + timedelta(days=1) - timedelta(microseconds=1)
    else:
        start = _parse_local(request.start or "", zone)
        end = _parse_local(request.end or "", zone)
    if start >= end:
        raise ValueError("Start must be earlier than end")
    if end - start > timedelta(days=31):
        raise ValueError("Choose a range of 31 days or less")
    return start, end


manager = JobManager()
app = FastAPI(title="AIJournalist Control Desk", docs_url=None, redoc_url=None)
app.mount("/assets", StaticFiles(directory=WEB_DIR), name="assets")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/config")
def config_status():
    settings = Settings()
    zone = ZoneInfo(settings.timezone)
    now = datetime.now(zone).replace(second=0, microsecond=0)
    return {
        "openrouter_configured": bool(settings.openrouter_api_key),
        "site_credentials_configured": bool(settings.site_username and settings.site_password),
        "model": settings.openrouter_model,
        "sources": ["NDTV India", "Times of India — India"],
        "site_api_url": settings.site_api_url,
        "timezone": settings.timezone,
        "defaults": {
            "date": now.strftime("%Y-%m-%d"),
            "start": (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M"),
            "end": now.strftime("%Y-%m-%dT%H:%M"),
            "max_articles": settings.max_articles,
        },
    }


@app.post("/api/jobs", status_code=202)
def create_job(request: ResearchRequest):
    settings = Settings()
    try:
        start, end = resolve_range(request, settings.timezone)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    job = manager.create(start, end, request.max_articles)
    return manager.snapshot(job.id)


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    try:
        return manager.snapshot(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc


@app.get("/api/jobs/{job_id}/previews/{preview_id}/markdown", response_class=PlainTextResponse)
def download_markdown(job_id: str, preview_id: str):
    try:
        job = manager.get(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    with manager.lock:
        preview = next((item for item in job.previews if item.id == preview_id), None)
        if not preview:
            raise HTTPException(status_code=404, detail="Preview not found")
        safe_name = "-".join(re.findall(r"[a-z0-9]+", preview.article.title.lower()))[:80] or "article"
        document = (
            f"# {preview.article.title}\n\n"
            f"## Summary\n\n{preview.article.summary}\n\n"
            f"{preview.article.content_markdown}\n\n"
            "---\n\n"
            f"Source: [{preview.source.source_name}]({preview.source.attribution_url})  \n"
            f"Originally published: {preview.source.published_at.isoformat()}\n"
        )
    return PlainTextResponse(
        document,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.md"'},
    )


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    try:
        job = manager.cancel(job_id)
        return manager.snapshot(job.id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc


@app.post("/api/jobs/{job_id}/publish", status_code=202)
def publish_job(job_id: str, request: PublishRequest):
    settings = Settings()
    if not settings.site_username or not settings.site_password:
        raise HTTPException(status_code=400, detail="Add SITE_USERNAME and SITE_PASSWORD to .env before publishing")
    try:
        job = manager.publish(job_id, request.preview_ids, request.status)
        return manager.snapshot(job.id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


if __name__ == "__main__":
    import threading as browser_threading
    import webbrowser

    import uvicorn

    url = "http://127.0.0.1:8787"
    print(f"AIJournalist Control Desk: {url}")
    browser_threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host="127.0.0.1", port=8787, log_level="warning")
