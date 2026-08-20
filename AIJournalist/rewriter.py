from __future__ import annotations

import json
import re
from typing import Any

from bs4 import BeautifulSoup
from openrouter import OpenRouter
from openrouter.errors import BadRequestResponseError
from openrouter.utils.retries import BackoffStrategy, RetryConfig

from models import RewrittenArticle, SourceArticle


DEFAULT_CATEGORIES = ["Politics", "World", "Economy", "Technology", "Culture", "Opinion", "Sports", "Science"]

SYSTEM_PROMPT = """You are a senior professional news journalist and editor. Produce a completely rewritten, original, engaging, neutral news report based on the supplied text.

Rules:
- Rewrite the headline (title), summary, and body text completely in fresh, original wording; never copy sentences verbatim.
- Do NOT mention the original publisher name, source website, news agency, or original URLs anywhere in the title, summary, or body text. Produce a standalone, original report.
- Do not add fake facts, fake quotes, or invented information not present in the material.
- Preserve real names, dates, figures, locations, and facts accurately.
- Do not mention being an AI.
- Return JSON only, with keys: title, summary, content_markdown, category, tags.
- title: engaging, fresh, factual headline under 140 characters.
- summary: a substantial 60-100 word overview in 3-5 sentences, under 800 characters.
- content_markdown: a comprehensive news report in Markdown format with clear paragraphs and section headings. Do not use HTML.
- category: exactly one supplied category.
- tags: an array of 3-7 short string keywords.
"""



def _extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("OpenRouter did not return a JSON object")
        value = json.loads(cleaned[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("OpenRouter response must be a JSON object")
    return value


def _fallback_category(article: SourceArticle, categories: list[str] | None = None) -> str:
    allowed = categories or DEFAULT_CATEGORIES
    material = f"{article.title} {article.description}".lower()
    rules = (
        ("Politics", ("parliament", "minister", "government", "election", "court", "policy")),
        ("Economy", ("economy", "market", "business", "rupee", "bank", "trade")),
        ("Technology", ("technology", "software", "ai ", "digital", "internet", "startup")),
        ("Sports", ("sport", "cricket", "football", "match", "tournament")),
        ("Science", ("science", "space", "research", "health", "climate")),
        ("Culture", ("film", "culture", "music", "festival", "actor")),
    )
    lookup = {item.casefold(): item for item in allowed}
    for category, terms in rules:
        if category.casefold() in lookup and any(term in material for term in terms):
            return lookup[category.casefold()]
    return "World" if "World" in allowed else allowed[0]


def _first_value(data: dict[str, Any], *names: str) -> Any:
    for name in names:
        value = data.get(name)
        if value not in (None, "", [], {}):
            return value
    return None


def _summary_from_markdown(content: str) -> str:
    plain = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", content)
    plain = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", plain)
    plain = re.sub(r"^[#>*+\-]+\s*", "", plain, flags=re.MULTILINE)
    plain = re.sub(r"[*_`~]", "", plain)
    plain = " ".join(plain.split())
    if len(plain) <= 780:
        return plain
    shortened = plain[:780].rsplit(" ", 1)[0].rstrip(" ,;:")
    return f"{shortened}…"


def build_source_fallback(article: SourceArticle, categories: list[str] | None = None) -> RewrittenArticle:
    """Create an attributed internal draft from extracted copy when AI is unavailable."""
    summary_material = " ".join((article.description or article.text or article.title).split())
    summary = summary_material[:780].rstrip()
    if len(summary) < 10:
        summary = article.title[:780]
    extracted_copy = (article.text or article.description or article.title).strip()[:20_000]
    return RewrittenArticle(
        title=article.title[:220],
        summary=summary,
        content_markdown=extracted_copy,
        category=_fallback_category(article, categories),
        tags=["India", "News", getattr(article, "category", "General")],
    )



class OpenRouterRewriter:
    def __init__(
        self,
        api_key: str,
        model: str = "openrouter/free",
        timeout: int = 30,
        site_url: str = "",
        app_name: str = "AIJournalist",
        client: OpenRouter | None = None,
    ):
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY is missing")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.site_url = site_url
        self.app_name = app_name
        self.client = client or OpenRouter(
            api_key=api_key,
            http_referer=site_url or None,
            x_open_router_title=app_name,
            timeout_ms=timeout * 1000,
            retry_config=RetryConfig(
                strategy="none",
                backoff=BackoffStrategy(
                    initial_interval=0,
                    max_interval=0,
                    exponent=1.0,
                    max_elapsed_time=0,
                    jitter_ms=0,
                ),
                retry_connection_errors=False,
            ),
        )

    def rewrite(self, article: SourceArticle, categories: list[str] | None = None) -> RewrittenArticle:
        allowed = categories or DEFAULT_CATEGORIES
        material = article.text or article.description
        if len(material.strip()) < 600:
            raise ValueError("Not enough source text for an accurate long-form rewrite")

        user_prompt = (
            f"Allowed categories: {json.dumps(allowed, ensure_ascii=False)}\n\n"
            "<SOURCE_MATERIAL>\n"
            f"Publisher: {article.source_name}\n"
            f"Published (UTC): {article.published_at.isoformat()}\n"
            f"Original headline: {article.title}\n"
            f"Article text: {material}\n"
            "</SOURCE_MATERIAL>"
        )
        request_body: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        try:
            response = self.client.chat.send(**request_body)
        except BadRequestResponseError as exc:
            # A routed free model may reject JSON mode even though it can still
            # follow the JSON-only prompt.
            if "response_format" not in str(exc).lower():
                raise RuntimeError(f"OpenRouter rejected the request: {exc}") from exc
            request_body.pop("response_format")
            response = self.client.chat.send(**request_body)
        except Exception as exc:
            raise RuntimeError(f"OpenRouter request failed: {exc}") from exc

        try:
            content = response.choices[0].message.content
            if not isinstance(content, str):
                raise TypeError("response content is not text")
        except (AttributeError, IndexError, TypeError) as exc:
            raise RuntimeError("OpenRouter returned an unexpected response") from exc

        try:
            data = _extract_json(content)
        except (ValueError, json.JSONDecodeError):
            # Some free routed models follow the Markdown request but ignore the
            # JSON envelope. Preserve a substantial AI draft instead of dropping it.
            if len(re.findall(r"\b[\w'-]+\b", content)) < 250:
                raise
            data = {"content_markdown": content}
        nested = _first_value(data, "article", "result", "story")
        if isinstance(nested, dict):
            data = {**data, **nested}
        title = str(_first_value(data, "title", "headline", "heading") or article.title).strip()[:220]
        content_value = _first_value(
            data,
            "content_markdown",
            "markdown",
            "body_markdown",
            "article_markdown",
            "content",
            "body",
            "article",
            "story",
        )
        if isinstance(content_value, list):
            content_value = "\n\n".join(str(item) for item in content_value)
        if not isinstance(content_value, str) or not content_value.strip():
            raise ValueError(f"OpenRouter JSON has no article body (fields: {', '.join(sorted(data))})")
        content_markdown = content_value.strip()
        if re.search(r"</?[a-z][^>]*>", content_markdown, flags=re.IGNORECASE):
            content_markdown = BeautifulSoup(content_markdown, "html.parser").get_text("\n\n", strip=True)
        summary_value = _first_value(data, "summary", "dek", "description", "abstract", "excerpt")
        summary = str(summary_value).strip()[:800] if summary_value else _summary_from_markdown(content_markdown)
        article_words = re.findall(r"\b[\w'-]+\b", content_markdown)
        # The prompt targets a much longer report. These are hard rejection
        # floors only, so a useful AI rewrite is not discarded for narrowly
        # missing the preferred length.
        if len(title) < 5 or len(summary) < 100 or len(article_words) < 250:
            raise ValueError("OpenRouter returned an unusably short article or summary")
        category = str(_first_value(data, "category", "section", "topic") or _fallback_category(article, allowed)).strip()
        category_lookup = {item.casefold(): item for item in allowed}
        if category.casefold() not in category_lookup:
            category = "World" if "World" in allowed else allowed[0]
        tag_value = _first_value(data, "tags", "keywords") or ["India", article.source_name, category]
        tags = tag_value if isinstance(tag_value, list) else str(tag_value).split(",")
        tags = [str(tag).strip()[:50] for tag in tags if str(tag).strip()][:7]

        return RewrittenArticle(
            title=title,
            summary=summary,
            content_markdown=content_markdown,
            category=category_lookup.get(category.casefold(), category),
            tags=tags,
        )
