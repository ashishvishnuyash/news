from __future__ import annotations

import html
import sqlite3
from pathlib import Path
from typing import Any

import requests

from models import RewrittenArticle, SourceArticle


class SiteClient:
    def __init__(self, base_url: str, username: str, password: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.api_root = self.base_url if self.base_url.lower().endswith("/api") else f"{self.base_url}/api"
        self.username = username
        self.password = password
        self.timeout = timeout
        self.session = requests.Session()

    def login(self) -> dict[str, Any]:
        if not self.username or not self.password:
            raise ValueError("SITE_USERNAME and SITE_PASSWORD are required for posting")
        response = self.session.post(
            f"{self.api_root}/auth/login",
            json={"username": self.username, "password": self.password},
            timeout=self.timeout,
        )
        self._raise(response, "Site login failed")
        payload = response.json()
        token = payload.get("access_token")
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"
        return payload["user"]

    def categories(self) -> list[str]:
        try:
            response = self.session.get(f"{self.api_root}/settings", timeout=self.timeout)
            response.raise_for_status()
            values = response.json().get("categories", [])
            return [str(item) for item in values if str(item).strip()]
        except (requests.RequestException, ValueError, AttributeError):
            return []

    def post(self, article: RewrittenArticle, source: SourceArticle, target_status: str = "DRAFT") -> dict[str, Any]:
        payload = article.site_payload()
        if source.image_url:
            payload["image_url"] = source.image_url
            payload["image_caption"] = (source.image_caption or "")[:300]
        response = self.session.post(f"{self.api_root}/articles", json=payload, timeout=self.timeout)

        self._raise(response, "Creating the site article failed")
        created = response.json()

        if target_status != "DRAFT":
            response = self.session.put(
                f"{self.api_root}/articles/{created['id']}",
                json={"status": target_status},
                timeout=self.timeout,
            )
            self._raise(response, f"Changing article {created['id']} to {target_status} failed")
            created = response.json()
        return created

    @staticmethod
    def _raise(response: requests.Response, context: str) -> None:
        if response.ok:
            return
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise RuntimeError(f"{context} (HTTP {response.status_code}): {detail}")


class PublicationLedger:
    def __init__(self, path: Path):
        self.connection = sqlite3.connect(path)
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS publications (
                source_identity TEXT PRIMARY KEY,
                source_title TEXT NOT NULL,
                site_article_id INTEGER NOT NULL,
                site_status TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        self.connection.commit()

    def contains(self, source: SourceArticle) -> bool:
        row = self.connection.execute(
            "SELECT 1 FROM publications WHERE source_identity = ? OR lower(source_title) = lower(?)",
            (source.identity, source.title),
        ).fetchone()
        return row is not None

    def record(self, source: SourceArticle, site_article_id: int, site_status: str) -> None:
        self.connection.execute(
            "INSERT OR REPLACE INTO publications(source_identity, source_title, site_article_id, site_status) VALUES (?, ?, ?, ?)",
            (source.identity, source.title, site_article_id, site_status),
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()
