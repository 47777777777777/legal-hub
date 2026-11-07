import sqlite3

conn = sqlite3.connect('data/legal_hub.db')
c = conn.cursor()

cnt = c.execute("SELECT count(*) FROM articles WHERE title IS NOT NULL AND title <> ''").fetchone()[0]
print(f"SELECT count(*) FROM articles WHERE title IS NOT NULL AND title <> '': {cnt}")

print("\nSELECT title_source, count(*) FROM articles GROUP BY title_source:")
for r in c.execute("SELECT title_source, count(*) FROM articles GROUP BY title_source").fetchall():
    print(f"  {repr(r[0]):<15}: {r[1]}")

