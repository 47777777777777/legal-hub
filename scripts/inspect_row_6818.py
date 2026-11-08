import sqlite3
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

conn = sqlite3.connect("data/legal_hub.db")
cur = conn.cursor()
cur.execute("SELECT reason FROM article_reasons WHERE id=6818")
print(cur.fetchone()[0])
conn.close()

