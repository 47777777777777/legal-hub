import sqlite3

conn = sqlite3.connect('data/legal_hub.db')
c = conn.cursor()
c.execute("PRAGMA table_info(acts)")
print("ACTS COLUMNS:", c.fetchall())

c.execute("PRAGMA table_info(articles)")
print("ARTICLES COLUMNS:", c.fetchall())

c.execute("SELECT id, name, pcode, status FROM acts LIMIT 5")
for r in c.fetchall():
    print("SAMPLE ACT:", r)
conn.close()

