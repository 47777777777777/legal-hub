import sys
import sqlite3

sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('data/legal_hub.db')
c = conn.cursor()

c.execute("SELECT id, pcode, name FROM acts WHERE id IN ('civil_code', 'criminal_code', 'constitution')")
for row in c.fetchall():
    print("act:", row)

c.execute("SELECT act_id, article_no, title, title_source FROM articles WHERE act_id='civil_code' AND article_no IN ('1', '2')")
for row in c.fetchall():
    print("civil_code art:", row)
