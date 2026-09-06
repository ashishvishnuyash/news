import asyncio
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv("AIJournalist/.env")
load_dotenv("backend/.env")

async def verify():
    engine = create_async_engine(os.getenv("DATABASE_URL"))
    async with engine.connect() as conn:
        res = await conn.execute(text("""
            SELECT id, title, slug, category, status, image_url IS NOT NULL as has_image, 
                   length(content) as content_len, length(summary) as summary_len,
                   published_at
            FROM articles 
            WHERE published_at >= '2026-08-13'
            ORDER BY id DESC
        """))
        rows = res.fetchall()
        print(f"Total Articles Ingested (Since Aug 13, 2026): {len(rows)}")
        print("\nRecent 15 Articles Sample:")
        for r in rows[:15]:
            print(f"  #{r[0]} [{r[3]}] ({r[4]}) len:{r[6]} has_img:{r[5]} pub:{r[8]}")
            print(f"     Title: {r[1]}")
            print(f"     Slug:  {r[2]}")
            
        print("\nCategory Distribution:")
        cat_res = await conn.execute(text("""
            SELECT category, count(*) 
            FROM articles 
            WHERE published_at >= '2026-08-13' 
            GROUP BY category 
            ORDER BY count(*) DESC
        """))
        for cat, cnt in cat_res.fetchall():
            print(f"  - {cat}: {cnt}")

        print("\nSample Detailed Content Inspection (#633):")
        sample_res = await conn.execute(text("""
            SELECT id, title, summary, content, image_url, tags, author_id, published_at
            FROM articles 
            WHERE id = 633
        """))
        sample = sample_res.fetchone()
        if sample:
            print(f"ID: {sample[0]}")
            print(f"Title: {sample[1]}")
            print(f"Summary: {sample[2]}")
            print(f"Image: {sample[4]}")
            print(f"Tags: {sample[5]}")
            print("Content Snippet (first 400 chars):")
            print(sample[3][:400])

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(verify())
