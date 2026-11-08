import sqlite3

conn = sqlite3.connect("data/legal_hub.db")
cur = conn.cursor()
cur.execute("SELECT id, act_id, duration_ms, created_at FROM source_attempts ORDER BY id DESC LIMIT 5")
for r in cur.fetchall():
    print(r)
conn.close()

