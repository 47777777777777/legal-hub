import sqlite3
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

conn = sqlite3.connect("data/legal_hub.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

for rid in [16975, 16997, 16998]:
    cur.execute("SELECT ar.*, a.name as act_name FROM article_reasons ar JOIN acts a ON ar.act_id = a.id WHERE ar.id = ?", (rid,))
    row = dict(cur.fetchone())
    print(f"\n=== id={rid}: {row['act_name']} ({row['act_id']}) Art {row['article_no']} ({row['version_date']}) ===")
    print("Reason:", row["reason"])

conn.close()

