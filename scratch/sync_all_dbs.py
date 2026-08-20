import os, sqlite3, glob

for db_path in glob.glob("**/*.db", recursive=True) + glob.glob("**/*.sqlite3", recursive=True):
    try:
        conn = sqlite3.connect(db_path)
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        if 'articles' in tables:
            rows = conn.execute("SELECT id, title, published_at FROM articles WHERE slug LIKE '%stockwhisperer%' OR id = 539").fetchall()
            print(f"{db_path}: {rows}")
            # Update to Dec 2025 if found
            if rows:
                conn.execute("UPDATE articles SET published_at = '2025-12-20 10:00:00', created_at = '2025-12-20 09:30:00' WHERE slug LIKE '%stockwhisperer%' OR id = 539")
                conn.commit()
                print(f"Updated {db_path} successfully!")
        conn.close()
    except Exception as e:
        print(f"Error checking {db_path}: {e}")
