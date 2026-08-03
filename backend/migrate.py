"""
Migration script: adds new columns to existing SQLite database without dropping data.
Run this ONCE before starting the backend with the new models.
"""
import asyncio
import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "news.db")


async def migrate():
    async with aiosqlite.connect(DB_PATH) as db:
        # ── users table ──────────────────────────────────────────────────────
        # Note: SQLite can't add UNIQUE or non-constant defaults to existing tables.
        await safe_add_column(db, "users", "email", "TEXT")  # No UNIQUE on ALTER TABLE
        await safe_add_column(db, "users", "bio", "TEXT")
        await safe_add_column(db, "users", "is_active", "INTEGER NOT NULL DEFAULT 1")
        await safe_add_column(db, "users", "updated_at", "DATETIME")

        # ── articles table ───────────────────────────────────────────────────
        await safe_add_column(db, "articles", "tags", "TEXT")
        await safe_add_column(db, "articles", "view_count", "INTEGER NOT NULL DEFAULT 0")
        await safe_add_column(db, "articles", "image_caption", "TEXT")

        # ── comments table ───────────────────────────────────────────────────
        await safe_add_column(db, "comments", "is_deleted", "INTEGER NOT NULL DEFAULT 0")

        # ── notifications table (create if not exists) ───────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER NOT NULL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                type VARCHAR NOT NULL DEFAULT 'INFO',
                is_read INTEGER NOT NULL DEFAULT 0,
                link TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        await db.commit()
        print("Migration completed successfully.")


async def safe_add_column(db, table: str, column: str, definition: str):
    """Add a column if it doesn't already exist."""
    try:
        await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        print(f"  + Added column {table}.{column}")
    except Exception as e:
        if "duplicate column name" in str(e).lower():
            print(f"  ~ Column {table}.{column} already exists, skipping.")
        else:
            print(f"  ! Error adding {table}.{column}: {e}")


if __name__ == "__main__":
    asyncio.run(migrate())
