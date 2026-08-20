import sqlite3

conn = sqlite3.connect('backend/news.db')
cursor = conn.cursor()

cursor.execute("SELECT id, title, published_at, created_at FROM articles WHERE id = 539 OR slug LIKE '%stockwhisperer%'")
rows = cursor.fetchall()
print("Found articles before update:", rows)

cursor.execute("""
    UPDATE articles
    SET published_at = '2025-12-20 10:00:00',
        created_at = '2025-12-20 09:30:00',
        updated_at = '2025-12-20 10:00:00'
    WHERE id = 539 OR slug LIKE '%stockwhisperer%'
""")
conn.commit()

cursor.execute("SELECT id, title, published_at, created_at FROM articles WHERE id = 539 OR slug LIKE '%stockwhisperer%'")
rows_after = cursor.fetchall()
print("After update in backend/news.db:", rows_after)
conn.close()
