from __future__ import annotations

import json
import re
import time
from typing import Any

import requests
from bs4 import BeautifulSoup

from models import RewrittenArticle, SourceArticle


DEFAULT_CATEGORIES = ["Politics", "World", "Economy", "Technology", "Culture", "Opinion", "Sports", "Science", "General"]

FALLBACK_MODELS = [
    "openrouter/free",
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
    "liquid/lfm-2.5-2.6b:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
]

SYSTEM_PROMPT = """You are a senior professional news journalist and editor. Produce a completely rewritten, original, engaging, neutral news report based on the supplied text.

Rules:
- Rewrite the headline (title), summary, and body text completely in fresh, original wording; never copy sentences verbatim.
- Do NOT mention the original publisher name, source website, news agency (e.g. PTI, ANI, IANS, Reuters, The Hindu, NDTV, Times of India), or original URLs anywhere in the title, summary, or body text. Produce a standalone, original report.
- Do not add fake facts, fake quotes, or invented information not present in the material.
- Preserve real names, dates, figures, locations, and facts accurately.
- Do not mention being an AI.
- Return JSON only, with keys: title, summary, content_markdown, category, tags.
- title: engaging, fresh, factual headline under 140 characters.
- summary: a substantial 60-100 word overview in 3-5 sentences, under 800 characters.
- content_markdown: a comprehensive news report in Markdown format with clear paragraphs and section headings (## Heading). Do not use HTML.
- category: exactly one category from the allowed list.
- tags: an array of 3-7 short string keywords (e.g. ["India", "Economy", "RBI", "Finance"]).
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
            raise ValueError("LLM did not return a valid JSON object")
        value = json.loads(cleaned[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("LLM response must be a JSON object")
    return value


def _fallback_category(article: SourceArticle, categories: list[str] | None = None) -> str:
    allowed = categories or DEFAULT_CATEGORIES
    material = f"{article.title} {article.description}".lower()
    rules = (
        ("Politics", ("parliament", "minister", "government", "election", "court", "policy", "bjp", "congress", "aap", "lok sabha", "rajya sabha", "supreme court")),
        ("Economy", ("economy", "market", "business", "rupee", "bank", "trade", "rbi", "gdp", "inflation", "sensex", "nifty")),
        ("Technology", ("technology", "software", "ai ", "digital", "internet", "startup", "isro", "satellite", "tech")),
        ("Sports", ("sport", "cricket", "football", "match", "tournament", "bcci", "ipl", "olympics")),
        ("Science", ("science", "space", "research", "health", "climate", "environment")),
        ("Culture", ("film", "culture", "music", "festival", "actor", "cinema", "bollywood")),
    )
    lookup = {item.casefold(): item for item in allowed}
    for category, terms in rules:
        if category.casefold() in lookup and any(term in material for term in terms):
            return lookup[category.casefold()]
    return "India" if "India" in allowed else allowed[0]


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


def clean_editorial_text(text_val: str) -> str:
    """Strip out agency markers, bylines, and source attributions."""
    s = text_val
    s = re.sub(r"^(PTI|ANI|IANS|Reuters|Bloomberg|AP|PTI-Bhasha)\s*[:-]\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\b(PTI|ANI|IANS|The Hindu|NDTV|Times of India|Indian Express|Hindustan Times|Livemint)\b", "", s, flags=re.IGNORECASE)
    s = re.sub(r"Source:.*$", "", s, flags=re.IGNORECASE | re.MULTILINE)
    s = re.sub(r"Also Read:.*$", "", s, flags=re.IGNORECASE | re.MULTILINE)
    s = re.sub(r"Click here to.*$", "", s, flags=re.IGNORECASE | re.MULTILINE)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def build_source_fallback(article: SourceArticle, categories: list[str] | None = None) -> RewrittenArticle:
    """Create an original, clean editorial draft from extracted copy when LLM is unavailable."""
    summary_material = clean_editorial_text(article.description or article.text or article.title)
    summary = " ".join(summary_material.split())[:780].rstrip()
    if len(summary) < 10:
        summary = article.title[:780]
    
    extracted_copy = clean_editorial_text(article.text or article.description or article.title)[:25_000]
    
    paragraphs = [p.strip() for p in extracted_copy.split("\n\n") if len(p.strip()) > 30]
    if not paragraphs:
        paragraphs = [extracted_copy]
    
    formatted_md = "\n\n".join(paragraphs)

    clean_title = re.sub(r"\s*[-|]\s*(NDTV|The Hindu|Times of India|Indian Express|Mint|PTI|ANI).*$", "", article.title, flags=re.IGNORECASE).strip()
    
    cat = _fallback_category(article, categories)
    return RewrittenArticle(
        title=clean_title[:220],
        summary=summary,
        content_markdown=formatted_md,
        category=cat,
        tags=["India", "News", cat, "National"],
    )


class OpenRouterRewriter:
    def __init__(
        self,
        api_key: str,
        model: str = "openrouter/free",
        timeout: int = 30,
        site_url: str = "http://localhost:3000",
        app_name: str = "AIJournalist",
    ):
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY is missing")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.site_url = site_url
        self.app_name = app_name

    def rewrite(self, article: SourceArticle, categories: list[str] | None = None) -> RewrittenArticle:
        allowed = categories or DEFAULT_CATEGORIES
        material = (article.text or article.description or "").strip()
        if len(material) < 250:
            raise ValueError("Not enough source text for an accurate long-form rewrite")

        user_prompt = (
            f"Allowed categories: {json.dumps(allowed, ensure_ascii=False)}\n\n"
            "<SOURCE_MATERIAL>\n"
            f"Headline: {article.title}\n"
            f"Published Date (UTC): {article.published_at.isoformat()}\n"
            f"Source Text:\n{material[:8000]}\n"
            "</SOURCE_MATERIAL>"
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.site_url,
            "X-Title": self.app_name,
        }

        # Try active model first, then fallback models if rate-limited or error occurs
        models_to_try = [self.model, "google/gemma-4-31b-it:free", "google/gemma-4-26b-a4b-it:free", "liquid/lfm-2.5-2.6b:free"]
        last_error = None

        for current_model in models_to_try:
            request_body: dict[str, Any] = {
                "model": current_model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.25,
                "response_format": {"type": "json_object"},
            }

            try:
                resp = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=request_body,
                    timeout=min(self.timeout, 12),
                )
                if resp.status_code == 400 and "response_format" in resp.text:
                    request_body.pop("response_format", None)
                    resp = requests.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers=headers,
                        json=request_body,
                        timeout=min(self.timeout, 12),
                    )

                if resp.status_code == 429:
                    last_error = f"Rate limited on {current_model}"
                    continue

                if not resp.ok:
                    last_error = f"HTTP {resp.status_code} ({current_model}): {resp.text[:100]}"
                    continue

                data_json = resp.json()
                content = data_json["choices"][0]["message"]["content"]
                if not content:
                    continue

                data = _extract_json(content)
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
                
                if not isinstance(content_value, str) or len(content_value.strip()) < 100:
                    continue

                content_markdown = clean_editorial_text(content_value.strip())
                summary_value = _first_value(data, "summary", "dek", "description", "abstract", "excerpt")
                summary = str(summary_value).strip()[:800] if summary_value else _summary_from_markdown(content_markdown)

                category = str(_first_value(data, "category", "section", "topic") or _fallback_category(article, allowed)).strip()
                category_lookup = {item.casefold(): item for item in allowed}
                mapped_category = category_lookup.get(category.casefold(), _fallback_category(article, allowed))

                tag_value = _first_value(data, "tags", "keywords") or ["India", "National", mapped_category]
                tags = tag_value if isinstance(tag_value, list) else str(tag_value).split(",")
                tags = [clean_editorial_text(str(t)).strip()[:50] for t in tags if str(t).strip()][:7]

                return RewrittenArticle(
                    title=clean_editorial_text(title),
                    summary=summary,
                    content_markdown=content_markdown,
                    category=mapped_category,
                    tags=tags,
                )

            except Exception as exc:
                last_error = str(exc)
                continue

        raise RuntimeError(f"OpenRouter rewrite failed across models: {last_error}")
