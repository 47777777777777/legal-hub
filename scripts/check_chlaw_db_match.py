import json
import sqlite3

conn = sqlite3.connect("data/legal_hub.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

with open("data/ChLaw.json", "r", encoding="utf-8-sig") as f:
    chlaw = json.load(f)

laws = chlaw.get("Laws", [])
print(f"Total Laws in ChLaw.json: {len(laws)}")

matched_by_pcode = 0
matched_by_name = 0
not_in_db = []

for l in laws:
    name = l.get("LawName")
    pcode = l.get("LawURL", "").split("PCode=")[-1].strip() if "PCode=" in l.get("LawURL", "") else ""
    # check in DB
    cur.execute("SELECT id, name, pcode FROM acts WHERE pcode = ?", (pcode,))
    row = cur.fetchone()
    if row:
        matched_by_pcode += 1
    else:
        cur.execute("SELECT id, name, pcode FROM acts WHERE name = ?", (name,))
        row2 = cur.fetchone()
        if row2:
            matched_by_name += 1
        else:
            not_in_db.append((name, pcode))

print(f"Matched by pcode: {matched_by_pcode}")
print(f"Matched by name only: {matched_by_name}")
print(f"Not in DB: {len(not_in_db)}")
if not_in_db:
    print("First 5 not in DB:", not_in_db[:5])

