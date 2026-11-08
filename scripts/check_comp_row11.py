import sqlite3

conn = sqlite3.connect(r'C:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub\data\legal_hub.db')
c = conn.cursor()
row = c.execute("SELECT id, act_id, article_no, new_version_date, old_version_date, source_url, raw_path, reason, length(reason) FROM article_comparison WHERE act_id='admin_procedure_act' AND article_no='128'").fetchone()

print("Row in article_comparison:")
print("  id:", row[0])
print("  act_id:", row[1])
print("  article_no:", row[2])
print("  new_version_date:", row[3])
print("  old_version_date:", row[4])
print("  source_url:", row[5])
print("  raw_path:", row[6])
print("  reason length:", row[8])
print("  reason head (100):", repr(row[7][:100]))

