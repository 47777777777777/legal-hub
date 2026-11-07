import sqlite3

conn = sqlite3.connect("data/legal_hub.db")
cur = conn.cursor()

cnt = cur.execute("SELECT count(*) FROM acts WHERE category LIKE '%廢止法規%'").fetchone()[0]
print(f"Acts with category containing 廢止法規: {cnt}")

cnt_active = cur.execute("SELECT count(*) FROM acts WHERE category LIKE '%廢止法規%' AND status = 'active'").fetchone()[0]
print(f"Acts with category 廢止法規 but status=active: {cnt_active}")

cnt_total = cur.execute("SELECT count(*) FROM acts").fetchone()[0]
print(f"Total acts: {cnt_total}")

