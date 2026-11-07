import sqlite3

conn = sqlite3.connect("data/legal_hub.db")
cur = conn.cursor()
cur.execute("SELECT status, count(*) FROM crawl_jobs WHERE act_id = 'civil_procedure_code' GROUP BY status")
print("crawl_jobs status counts for civil_procedure_code:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

