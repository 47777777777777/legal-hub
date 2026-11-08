import sqlite3

conn = sqlite3.connect(r'C:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub\data\legal_hub.db')
c = conn.cursor()

print("--- APA 128 versions ---")
rows = c.execute("SELECT id, act_id, article_no, version_date, date_label_raw, date_raw, action_type, length(content) FROM article_versions WHERE act_id='admin_procedure_act' AND article_no='128' ORDER BY version_date ASC").fetchall()
for r in rows:
    print(r)

print("--- APA 128 reasons ---")
rows = c.execute("SELECT id, act_id, article_no, version_date, date_label_raw, date_raw, length(reason) FROM article_reasons WHERE act_id='admin_procedure_act' AND article_no='128' ORDER BY version_date ASC").fetchall()
for r in rows:
    print(r)

print("--- Criminal code 10 versions ---")
rows = c.execute("SELECT id, act_id, article_no, version_date, date_label_raw, date_raw, action_type, length(content) FROM article_versions WHERE act_id='criminal_code' AND article_no='10' ORDER BY version_date ASC").fetchall()
for r in rows:
    print(r)

