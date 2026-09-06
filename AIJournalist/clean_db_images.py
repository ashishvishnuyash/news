import os
import re
import sys
from dotenv import load_dotenv
import psycopg2

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv("AIJournalist/.env")
load_dotenv("backend/.env")

PLACEHOLDER_REGEX = re.compile(
    r"("
    r"thehindu\.com/theme/"
    r"|thehindu\.com/.*og[-_]image"
    r"|thehindu\.com/.*default"
    r"|thehindu\.com/static/"
    r"|thehindu\.com/.*logo"
    r"|th-i\.thgim\.com/.*og[-_]image"
    r"|th-i\.thgim\.com/.*default"
    r"|th-i\.thgim\.com/.*logo"
    r"|thehindu-logo"
    r"|ndtv\.com/.*logo"
    r"|ndtv\.com/.*placeholder"
    r"|ndtv\.com/.*default"
    r"|ndtv\.com/common/"
    r"|ndtvimg\.com/.*logo"
    r"|indianexpress\.com/.*logo"
    r"|indianexpress\.com/.*default"
    r"|indianexpress\.com/theme/"
    r"|livemint\.com/.*logo"
    r"|livemint\.com/.*default"
    r"|static\.toiimg\.com/.*default"
    r"|timesofindia.*logo"
    r"|timesofindia.*placeholder"
    r"|placeholder"
    r"|default_avatar"
    r"|default-news"
    r"|fallback"
    r"|dummy"
    r"|site-logo"
    r"|brand-logo"
    r"|favicon"
    r"|/logo/"
    r"|/logos/"
    r"|logo\.(png|jpg|jpeg|webp|svg|gif)"
    r"|\.ico"
    r")",
    re.IGNORECASE,
)

PUBLISHER_CAPTION_REGEX = re.compile(
    r"(the hindu|ndtv|times of india|livemint|indian express|pti|ani|via |source image)",
    re.IGNORECASE,
)

def clean_database_images():
    host = os.getenv("PGHOST", "newsql.postgres.database.azure.com")
    user = os.getenv("PGUSER", "azureuser")
    password = os.getenv("PGPASSWORD", "Cywar@exe248")
    database = os.getenv("PGDATABASE", "postgres")
    port = int(os.getenv("PGPORT", "5432"))

    print(f"Connecting to {host}:{port}/{database} as {user} (sslmode=require)...")
    conn = psycopg2.connect(
        host=host,
        user=user,
        password=password,
        dbname=database,
        port=port,
        sslmode="require",
        connect_timeout=10,
    )
    conn.autocommit = True
    cur = conn.cursor()
    print("Connected successfully!")

    cur.execute("SELECT id, title, image_url, image_caption, category FROM articles ORDER BY id ASC")
    rows = cur.fetchall()
    print(f"Total articles in database: {len(rows)}")

    nullify_ids = []
    clean_caption_ids = []

    for r in rows:
        art_id = r[0]
        image_url = r[2]
        image_caption = r[3]

        if image_url and PLACEHOLDER_REGEX.search(image_url.strip()):
            nullify_ids.append(art_id)
        elif image_url and image_caption and PUBLISHER_CAPTION_REGEX.search(image_caption):
            clean_caption_ids.append(art_id)

    print(f"Identified {len(nullify_ids)} articles with publisher placeholders/logos.")
    print(f"Identified {len(clean_caption_ids)} articles with publisher mentions in captions.")

    if nullify_ids:
        cur.execute("UPDATE articles SET image_url = NULL, image_caption = NULL WHERE id = ANY(%s)", (nullify_ids,))
        print(f"[✓] Nullified images & captions on {len(nullify_ids)} articles.")

    if clean_caption_ids:
        cur.execute("UPDATE articles SET image_caption = 'Special Report' WHERE id = ANY(%s)", (clean_caption_ids,))
        print(f"[✓] Sanitized captions on {len(clean_caption_ids)} articles.")

    # Ensure any remaining articles with NULL image_url also have NULL image_caption
    cur.execute("UPDATE articles SET image_caption = NULL WHERE image_url IS NULL AND image_caption IS NOT NULL")

    # Post-verification
    cur.execute("SELECT count(*) FROM articles WHERE image_url IS NOT NULL")
    valid_images = cur.fetchone()[0]

    cur.execute("""
        SELECT count(*) FROM articles 
        WHERE image_caption ILIKE '%the hindu%' 
           OR image_caption ILIKE '%ndtv%' 
           OR image_caption ILIKE '%times of india%' 
           OR image_caption ILIKE '%livemint%' 
           OR image_caption ILIKE '%indian express%' 
           OR image_caption ILIKE '%via %'
    """)
    leaking = cur.fetchone()[0]

    print(f"\nVerification Results:")
    print(f"  - Total articles with valid news photos: {valid_images}")
    print(f"  - Total articles with publisher mentions in captions: {leaking}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    clean_database_images()
