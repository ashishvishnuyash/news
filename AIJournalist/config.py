from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True, slots=True)
class Settings:
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "").strip()
    openrouter_model: str = os.getenv("OPENROUTER_MODEL", "openrouter/free").strip()
    openrouter_site_url: str = os.getenv("OPENROUTER_SITE_URL", "").strip()
    openrouter_app_name: str = os.getenv("OPENROUTER_APP_NAME", "AIJournalist").strip()
    site_api_url: str = os.getenv("SITE_API_URL", "http://localhost:8000").rstrip("/")
    site_username: str = os.getenv("SITE_USERNAME", "").strip()
    site_password: str = os.getenv("SITE_PASSWORD", "")
    timezone: str = os.getenv("DEFAULT_TIMEZONE", "Asia/Kolkata").strip()
    max_articles: int = int(os.getenv("DEFAULT_MAX_ARTICLES", "5"))
    timeout: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))

