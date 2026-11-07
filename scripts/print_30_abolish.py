import csv

with open("reports/moj_dryrun_abolish_322.csv", "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

print(f"Total abolish rows: {len(rows)}")
for i, r in enumerate(rows[:30], 1):
    print(f"{i:2d}. act_id={r['act_id']}, pcode={r['pcode']}, name={r['name']}, cat={r['category']}, db_status={r['current_db_status']}, abandon_note={r['incoming_abandon_note']}, mod_date={r['incoming_modified_date']}")

