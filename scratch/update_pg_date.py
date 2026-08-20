import asyncio
import asyncpg
from datetime import datetime

DATABASE_URL = "postgresql://azureuser:Cywar%40exe248@newsql.postgres.database.azure.com:5432/postgres"

async def update_published_date():
    conn = await asyncpg.connect(DATABASE_URL)
    print("Connected to PostgreSQL on Azure!")
    
    # Query current row
    row = await conn.fetchrow("SELECT id, title, published_at, created_at FROM articles WHERE id = 539")
    print("Before update:", row)
    
    dec_2025_date = datetime(2025, 12, 20, 10, 0, 0)
    
    await conn.execute("""
        UPDATE articles
        SET published_at = $1,
            created_at = $2,
            updated_at = $1
        WHERE id = 539
    """, dec_2025_date, datetime(2025, 12, 20, 9, 30, 0))
    
    row_after = await conn.fetchrow("SELECT id, title, published_at, created_at FROM articles WHERE id = 539")
    print("After update:", row_after)
    
    await conn.close()

asyncio.run(update_published_date())
