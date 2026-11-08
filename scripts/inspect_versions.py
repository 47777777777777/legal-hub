import sqlite3

conn = sqlite3.connect(r'C:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub\data\legal_hub.db')
c = conn.cursor()
cols = [r[1] for r in c.execute('PRAGMA table_info(article_versions)').fetchall()]
print('Columns of article_versions:', cols)

rows = c.execute('SELECT act_id, article_no, version_date, content FROM article_versions LIMIT 5').fetchall()
for r in rows:
    print(r[0], r[1], r[2], repr(r[3][:30]))

