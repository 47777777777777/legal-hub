import sqlite3
import json

conn = sqlite3.connect("data/legal_hub.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=== article_reasons for Art 128 ===")
reasons = cur.execute("SELECT * FROM article_reasons WHERE act_id = 'admin_procedure_act' AND article_no = '128'").fetchall()
for r in reasons:
    print(f"ID={r['id']}, version_date={r['version_date']}, action_type={r['action_type']}, date_label_raw={r['date_label_raw']}, raw_path={r['raw_path']}")
    print(f"Reason full text:\n{r['reason']}\n---")

print("\n=== article_comparison for Art 128 ===")
comps = cur.execute("SELECT * FROM article_comparison WHERE act_id = 'admin_procedure_act' AND article_no = '128'").fetchall()
for c in comps:
    print(f"ID={c['id']}, new_date={c['new_version_date']}, old_date={c['old_version_date']}, action_type={c['action_type']}, date_label_raw={c['date_label_raw']}")
    print(f"col_headers_json: {c['col_headers_json']}")
    print(f"cells_json: {c['cells_json']}")
    print(f"reason: {c['reason']}")
    print(f"raw_path: {c['raw_path']}\n---")

