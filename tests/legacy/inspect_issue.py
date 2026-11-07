import sqlite3
import json

conn = sqlite3.connect('data/legal_hub.db')
c = conn.cursor()

c.execute("PRAGMA table_info(articles)")
print("articles columns:", [col[1] for col in c.fetchall()])

c.execute("SELECT id, act_id, article_no, title, title_source FROM articles WHERE act_id='civil_code' AND article_no='1'")
for row in c.fetchall():
    print("articles row 1:", row)

c.execute("SELECT act_id, article_no, source, source_url FROM article_enrichments WHERE act_id='civil_code' AND article_no='1'")
print("enrichments row 1:", c.fetchall())

# Also check acts table
c.execute("SELECT id, title, category FROM acts WHERE id IN ('civil_code', 'criminal_code', 'constitution')")
for row in c.fetchall():
    print("acts row:", row)

