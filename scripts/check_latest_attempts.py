import sqlite3
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

conn = sqlite3.connect("data/legal_hub.db")
cur = conn.cursor()
cur.execute("SELECT sa.id, sa.act_id, a.name, sa.status, sa.created_at FROM source_attempts sa LEFT JOIN acts a ON sa.act_id = a.id ORDER BY sa.id DESC LIMIT 10")
for r in cur.fetchall():
    print(r)
conn.close()

