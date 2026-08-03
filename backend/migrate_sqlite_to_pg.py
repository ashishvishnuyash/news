"""
SQLite to PostgreSQL Data Migration Script using Pydantic & SQLAlchemy Async.

This script reads all data from a local SQLite database, validates and serializes
each row using Pydantic DTO models, creates target tables on PostgreSQL, inserts
the data maintaining foreign keys and primary keys, and resets PostgreSQL ID sequences.

Usage:
    python migrate_sqlite_to_pg.py [--sqlite-url SQLITE_URL] [--pg-url PG_URL]
"""

import asyncio
import argparse
import os
import sys
import urllib.parse
from typing import Optional, List, Type, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, text

# Import project settings and models
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.config import settings
from app.models import Base, User, Article, Comment, ReviewComment, Notification, SiteSetting


# ──────────────────────────────────────────────────────────────
# Pydantic Migration Models (Data Transfer Objects)
# ──────────────────────────────────────────────────────────────

class UserDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: Optional[str] = None
    hashed_password: str
    role: str = "READER"
    bio: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class ArticleDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: Optional[str] = None
    content: str
    summary: Optional[str] = None
    status: str = "DRAFT"
    category: str = "General"
    image_url: Optional[str] = None
    image_caption: Optional[str] = None
    tags: Optional[str] = None
    view_count: int = 0
    is_pinned: bool = False
    is_breaking: bool = False
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None
    author_id: int
    editor_id: Optional[int] = None


class CommentDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content: str
    created_at: datetime
    is_deleted: bool = False
    article_id: int
    author_id: int


class ReviewCommentDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content: str
    created_at: datetime
    article_id: int
    author_id: int


class NotificationDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    message: str
    type: str = "INFO"
    is_read: bool = False
    link: Optional[str] = None
    created_at: datetime


class SiteSettingDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    value: str
    description: Optional[str] = None
    updated_at: datetime


# ──────────────────────────────────────────────────────────────
# Migration Logic
# ──────────────────────────────────────────────────────────────

async def migrate_table(
    sqlite_session: AsyncSession,
    pg_session: AsyncSession,
    orm_model: Any,
    dto_class: Type[BaseModel],
    table_name: str,
    sequence_name: Optional[str] = None,
) -> int:
    """Extract rows from SQLite, validate via Pydantic DTO, and load into PostgreSQL."""
    print(f"📦 Processing table: '{table_name}'...")
    
    # 1. Fetch from SQLite
    result = await sqlite_session.execute(select(orm_model))
    sqlite_rows = result.scalars().all()
    
    if not sqlite_rows:
        print(f"   ℹ️ No records found in SQLite for '{table_name}'. Skipping.")
        return 0

    # 2. Validate and serialize via Pydantic
    pydantic_models = [dto_class.model_validate(row) for row in sqlite_rows]
    print(f"   ✅ Validated {len(pydantic_models)} records with Pydantic ({dto_class.__name__}).")

    # 3. Re-instantiate ORM objects for PostgreSQL session insertion
    pg_objects = []
    max_id = 0
    for dto in pydantic_models:
        data_dict = dto.model_dump()
        if "id" in data_dict and data_dict["id"] > max_id:
            max_id = data_dict["id"]
        pg_objects.append(orm_model(**data_dict))

    # 4. Insert into PostgreSQL
    pg_session.add_all(pg_objects)
    await pg_session.commit()
    print(f"   🚀 Successfully migrated {len(pg_objects)} records to PostgreSQL table '{table_name}'.")

    # 5. Reset PostgreSQL auto-increment sequence if primary keys were preserved
    if sequence_name and max_id > 0:
        try:
            await pg_session.execute(
                text(f"SELECT setval('{sequence_name}', :max_id, true)"),
                {"max_id": max_id}
            )
            await pg_session.commit()
            print(f"   🔄 Reset sequence '{sequence_name}' to {max_id}.")
        except Exception as e:
            print(f"   ⚠️ Warning resetting sequence '{sequence_name}': {e}")

    return len(pg_objects)


async def run_migration(sqlite_url: str, pg_url: str):
    print("=" * 65)
    print(" 🔄 Starting SQLite -> PostgreSQL Migration via Pydantic")
    print("=" * 65)
    print(f"  Source (SQLite) : {sqlite_url}")
    print(f"  Target (Postgres): {pg_url.split('@')[-1] if '@' in pg_url else pg_url}")
    print("=" * 65)

    # Setup Engines
    sqlite_engine = create_async_engine(sqlite_url, connect_args={"check_same_thread": False})
    pg_engine = create_async_engine(pg_url)

    # Session Makers
    SqliteSession = async_sessionmaker(sqlite_engine, class_=AsyncSession, expire_on_commit=False)
    PgSession = async_sessionmaker(pg_engine, class_=AsyncSession, expire_on_commit=False)

    # Create tables in target PostgreSQL database
    print("\n🛠️ Creating database tables in target PostgreSQL...")
    async with pg_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ PostgreSQL tables ready.")

    total_records = 0

    async with SqliteSession() as sqlite_session, PgSession() as pg_session:
        # Order matters for foreign key constraints:
        # 1. Users
        # 2. SiteSettings
        # 3. Articles (depends on Users)
        # 4. Comments (depends on Articles, Users)
        # 5. ReviewComments (depends on Articles, Users)
        # 6. Notifications (depends on Users)
        
        tables_to_migrate = [
            (User, UserDTO, "users", "users_id_seq"),
            (SiteSetting, SiteSettingDTO, "site_settings", "site_settings_id_seq"),
            (Article, ArticleDTO, "articles", "articles_id_seq"),
            (Comment, CommentDTO, "comments", "comments_id_seq"),
            (ReviewComment, ReviewCommentDTO, "review_comments", "review_comments_id_seq"),
            (Notification, NotificationDTO, "notifications", "notifications_id_seq"),
        ]

        for orm_model, dto_class, table_name, seq_name in tables_to_migrate:
            count = await migrate_table(
                sqlite_session=sqlite_session,
                pg_session=pg_session,
                orm_model=orm_model,
                dto_class=dto_class,
                table_name=table_name,
                sequence_name=seq_name
            )
            total_records += count

    print("\n" + "=" * 65)
    print(f" 🎉 MIGRATION COMPLETE! Total records migrated: {total_records}")
    print("=" * 65 + "\n")


def get_pg_url_from_env() -> str:
    """Build PostgreSQL URL from env or fallback to settings."""
    pghost = os.getenv("PGHOST") or getattr(settings, "PGHOST", None)
    pguser = os.getenv("PGUSER") or getattr(settings, "PGUSER", "azureuser")
    pgpass = os.getenv("PGPASSWORD") or getattr(settings, "PGPASSWORD", "Cywar@exe248")
    pgport = os.getenv("PGPORT") or getattr(settings, "PGPORT", "5432")
    pgdb = os.getenv("PGDATABASE") or getattr(settings, "PGDATABASE", "postgres")

    if pghost:
        encoded_password = urllib.parse.quote_plus(pgpass)
        return f"postgresql+asyncpg://{pguser}:{encoded_password}@{pghost}:{pgport}/{pgdb}"
    
    # Check if DATABASE_URL starts with postgres
    if settings.DATABASE_URL.startswith("postgresql"):
        return settings.DATABASE_URL

    return f"postgresql+asyncpg://azureuser:{urllib.parse.quote_plus('Cywar@exe248')}@newsql.postgres.database.azure.com:5432/postgres"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate SQLite database to PostgreSQL via Pydantic DTOs.")
    parser.add_argument(
        "--sqlite-url",
        default="sqlite+aiosqlite:///./news.db",
        help="SQLite connection URL (default: sqlite+aiosqlite:///./news.db)"
    )
    parser.add_argument(
        "--pg-url",
        default=None,
        help="PostgreSQL connection URL (defaults to PGHOST/PGUSER/PGPASSWORD env vars or settings)"
    )

    args = parser.parse_args()
    target_pg_url = args.pg_url or get_pg_url_from_env()

    try:
        asyncio.run(run_migration(sqlite_url=args.sqlite_url, pg_url=target_pg_url))
    except Exception as e:
        print(f"\n❌ Migration error: {e}", file=sys.stderr)
        sys.exit(1)
