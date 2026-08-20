from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from markdown import markdown


@dataclass(slots=True)
class SourceArticle:
    title: str
    url: str
    published_at: datetime
    source_name: str
    description: str = ""
    text: str = ""
    original_url: str = ""
    image_url: str = ""
    image_caption: str = ""
    extraction_method: str = "RSS"
    category: str = "General"


    @property
    def identity(self) -> str:
        return self.url.strip().lower()

    @property
    def attribution_url(self) -> str:
        return self.original_url or self.url


@dataclass(slots=True)
class RewrittenArticle:
    title: str
    summary: str
    content_markdown: str
    category: str
    tags: list[str]

    def site_payload(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            # The site renders sanitized HTML. Markdown remains the canonical
            # generated format and is converted only at the publication edge.
            "content": markdown(self.content_markdown, extensions=["extra", "sane_lists"]),
            "category": self.category,
            "tags": ", ".join(self.tags),
            "image_url": None,
            "image_caption": None,
        }
