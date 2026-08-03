"""Small, dependency-free allowlist sanitizer for staff-authored article HTML."""

from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse

ALLOWED_TAGS = {
    "p", "br", "h2", "h3", "h4", "strong", "b", "em", "i", "u", "s",
    "blockquote", "ol", "ul", "li", "a", "code", "pre", "hr",
}
VOID_TAGS = {"br", "hr"}
DROP_CONTENT_TAGS = {"script", "style", "iframe", "object", "embed", "svg", "math"}


def _safe_link(value: str) -> bool:
    parsed = urlparse(value.strip())
    return parsed.scheme.lower() in {"", "http", "https", "mailto"}


class _Sanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.output: list[str] = []
        self.drop_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in DROP_CONTENT_TAGS:
            self.drop_depth += 1
            return
        if self.drop_depth or tag not in ALLOWED_TAGS:
            return
        clean_attrs: list[str] = []
        if tag == "a":
            values = {key.lower(): value for key, value in attrs if value is not None}
            href = values.get("href", "")
            if href and _safe_link(href):
                clean_attrs.append(f'href="{escape(href, quote=True)}"')
                clean_attrs.append('rel="noopener noreferrer"')
        suffix = f" {' '.join(clean_attrs)}" if clean_attrs else ""
        self.output.append(f"<{tag}{suffix}>")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in DROP_CONTENT_TAGS:
            self.drop_depth = max(0, self.drop_depth - 1)
            return
        if not self.drop_depth and tag in ALLOWED_TAGS and tag not in VOID_TAGS:
            self.output.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if not self.drop_depth:
            self.output.append(escape(data))


def sanitize_article_html(value: str) -> str:
    parser = _Sanitizer()
    parser.feed(value)
    parser.close()
    return "".join(parser.output).strip()


def plain_text(value: str) -> str:
    class _TextParser(HTMLParser):
        def __init__(self) -> None:
            super().__init__(convert_charrefs=True)
            self.parts: list[str] = []

        def handle_data(self, data: str) -> None:
            self.parts.append(data)

    parser = _TextParser()
    parser.feed(value)
    return " ".join(" ".join(parser.parts).split())
