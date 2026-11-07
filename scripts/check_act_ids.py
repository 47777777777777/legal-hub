import sqlite3

conn = sqlite3.connect("data/legal_hub.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT pcode, lp_name, lp_act_url FROM law_map")
tier1_rows = cur.fetchall()

print(f"{'pcode':<10} | {'acts.id':<25} | {'name':<15} | {'article_count'}")
print("-" * 70)
for r in tier1_rows:
    pcode = r["pcode"]
    cur.execute("SELECT id, name, pcode FROM acts WHERE pcode = ? OR UPPER(pcode) = ?", (pcode, pcode))
    act_row = cur.fetchone()
    if act_row:
        act_id = act_row["id"]
        cur.execute("SELECT count(*) FROM articles WHERE act_id = ?", (act_id,))
        count = cur.fetchone()[0]
        print(f"{pcode:<10} | {act_id:<25} | {act_row['name']:<15} | {count}")
    else:
        print(f"{pcode:<10} | NOT FOUND IN ACTS")
