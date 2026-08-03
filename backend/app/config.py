import urllib.parse
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DATABASE_URL: str = "sqlite+aiosqlite:///./news.db"
    PGHOST: Optional[str] = None
    PGUSER: Optional[str] = None
    PGPORT: Optional[str] = "5432"
    PGDATABASE: Optional[str] = None
    PGPASSWORD: Optional[str] = None
    SECRET_KEY: str = "supersecretnewspaperkeythatshouldbechangedinproduction"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    COOKIE_SECURE: bool = False
    COOKIE_DOMAIN: Optional[str] = None
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"
    CORS_ORIGIN_REGEX: str = r"https?://([a-z0-9-]+\.)?localhost:(3000|3001)"
    ALLOWED_HOSTS: str = "localhost,127.0.0.1,testserver"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def assemble_db_url(self) -> "Settings":
        if self.PGHOST and self.PGUSER and self.PGPASSWORD and self.PGDATABASE:
            encoded_password = urllib.parse.quote_plus(self.PGPASSWORD)
            port = self.PGPORT or "5432"
            self.DATABASE_URL = f"postgresql+asyncpg://{self.PGUSER}:{encoded_password}@{self.PGHOST}:{port}/{self.PGDATABASE}"
        return self


    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def allowed_hosts(self) -> list[str]:
        return [host.strip() for host in self.ALLOWED_HOSTS.split(",") if host.strip()]

settings = Settings()
