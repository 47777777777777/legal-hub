import sqlite3

conn = sqlite3.connect('data/legal_hub.db')
c = conn.cursor()
c.execute("SELECT act_id, article_no, content FROM articles WHERE act_id LIKE 'civil%' AND content LIKE '%有期徒刑%'")
rows = c.fetchall()
print("Found civil articles with 有期徒刑:", len(rows))
for r in rows:
    print(r[0], r[1], r[2][:40])

c.execute("SELECT act_id, article_no, content FROM articles WHERE act_id='civil_code' AND content LIKE '%過失%'")
rows = c.fetchall()
print("Found civil_code with 過失:", len(rows))
for r in rows[:3]:
    print(r[0], r[1], r[2][:40])

