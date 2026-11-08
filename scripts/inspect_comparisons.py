import sqlite3

conn = sqlite3.connect(r'C:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub\data\legal_hub.db')
c = conn.cursor()
rows = c.execute("SELECT id, act_id, article_no, new_version_date, old_version_date, length(new_content), length(old_content), reason FROM article_comparison").fetchall()
for r in rows:
    print(r[0], r[1], r[2], r[3], r[4], r[5], r[6], str(r[7])[:40])

