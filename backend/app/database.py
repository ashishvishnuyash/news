from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.config import settings

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_recycle=300,
)



SessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()


ARTICLE_COMPATIBILITY_COLUMNS = {
    "subtitle": "TEXT",
    "sources": "TEXT",
    "seo_title": "VARCHAR",
    "seo_description": "TEXT",
    "og_image_url": "VARCHAR",
    "article_type": "VARCHAR NOT NULL DEFAULT 'NEWS'",
    "fact_check_rating": "VARCHAR",
    "scheduled_at": "TIMESTAMP",
}

USER_COMPATIBILITY_COLUMNS = {
    "slug": "VARCHAR",
    "profile_image_url": "VARCHAR",
    "job_title": "VARCHAR",
    "coverage_areas": "TEXT",
    "social_links": "TEXT",
}


async def ensure_compatible_schema(connection) -> None:
    """Add nullable newsroom fields to existing SQLite/PostgreSQL databases.

    ``create_all`` creates new tables but intentionally does not alter existing
    ones. These additive columns keep old deployments compatible without
    dropping or rewriting publication data.
    """

    def existing_columns(sync_connection, table_name: str) -> set[str]:
        return {column["name"] for column in inspect(sync_connection).get_columns(table_name)}

    for table_name, columns in (
        ("articles", ARTICLE_COMPATIBILITY_COLUMNS),
        ("users", USER_COMPATIBILITY_COLUMNS),
    ):
        current = await connection.run_sync(existing_columns, table_name)
        for column_name, definition in columns.items():
            if column_name not in current:
                await connection.execute(text(f'ALTER TABLE {table_name} ADD COLUMN "{column_name}" {definition}'))

    if connection.dialect.name == "postgresql":
        # Older application workers incremented view_count through an ORM row
        # update, which also fired Article.updated_at's Python on-update value.
        # Keep the editorial timestamp stable whenever view_count is the only
        # substantive field changed, even during a rolling deployment.
        await connection.execute(text("""
            CREATE OR REPLACE FUNCTION preserve_article_timestamp_on_view()
            RETURNS trigger AS $$
            BEGIN
                IF NEW.view_count IS DISTINCT FROM OLD.view_count
                   AND (to_jsonb(NEW) - 'view_count' - 'updated_at')
                       IS NOT DISTINCT FROM
                       (to_jsonb(OLD) - 'view_count' - 'updated_at') THEN
                    NEW.updated_at := OLD.updated_at;
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
        """))
        await connection.execute(text("""
            DROP TRIGGER IF EXISTS preserve_article_timestamp_on_view
            ON articles
        """))
        await connection.execute(text("""
            CREATE TRIGGER preserve_article_timestamp_on_view
            BEFORE UPDATE ON articles
            FOR EACH ROW
            EXECUTE FUNCTION preserve_article_timestamp_on_view()
        """))

async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
