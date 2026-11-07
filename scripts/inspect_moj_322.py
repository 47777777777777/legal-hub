import sqlite3
import json
import csv
import os

conn = sqlite3.connect("data/legal_hub.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# 1. Query recorded update_runs
runs = cur.execute("SELECT run_id, source, started_at, status, counts_json FROM update_runs WHERE source = 'moj' ORDER BY started_at DESC LIMIT 5").fetchall()
print("Recent MOJ runs:")
for r in runs:
    print(dict(r))

# 2. Query recorded update_changes where change_type = 'abolish_act'
changes = cur.execute("SELECT * FROM update_changes WHERE change_type = 'abolish_act'").fetchall()
print(f"\nTotal abolish_act changes in DB: {len(changes)}")

# Let's map to acts table
act_ids = [c["act_id"] for c in changes]
print(f"Sample act_ids: {act_ids[:10]}")

os.makedirs("reports", exist_ok=True)
csv_path = os.path.join("reports", "moj_dryrun_abolish_322.csv")

rows_to_write = []
for c in changes:
    aid = c["act_id"]
    detail = json.loads(c["detail_json"]) if c["detail_json"] else {}
    act = cur.execute("SELECT id, pcode, name, category, status, last_modified, abandon_note FROM acts WHERE id = ?", (aid,)).fetchone()
    if act:
        rows_to_write.append({
            "act_id": act["id"],
            "pcode": act["pcode"],
            "name": act["name"],
            "category": act["category"],
            "current_db_status": act["status"],
            "db_abandon_note": act["abandon_note"],
            "incoming_abandon_note": detail.get("abandon_note"),
            "incoming_modified_date": detail.get("modified_date")
        })
    else:
        rows_to_write.append({
            "act_id": aid,
            "pcode": "",
            "name": detail.get("name", ""),
            "category": "",
            "current_db_status": "not_in_acts_table",
            "db_abandon_note": "",
            "incoming_abandon_note": detail.get("abandon_note"),
            "incoming_modified_date": detail.get("modified_date")
        })

print(f"Writing {len(rows_to_write)} rows to {csv_path}...")
with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
    if rows_to_write:
        writer = csv.DictWriter(f, fieldnames=list(rows_to_write[0].keys()))
        writer.writeheader()
        writer.writerows(rows_to_write)

print("Done. First 10 rows:")
for r in rows_to_write[:10]:
    print(r)

