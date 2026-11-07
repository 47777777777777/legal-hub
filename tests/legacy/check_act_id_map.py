import sqlite3

conn = sqlite3.connect('data/legal_hub.db')
c = conn.cursor()

print("Acts matching 行政程序法:")
for r in c.execute("SELECT id, name FROM acts WHERE name = '行政程序法' OR id = 'admin_procedure_act'").fetchall():
    print(" ", r)

print("Distinct act_id in article_reasons:")
for r in c.execute("SELECT DISTINCT act_id FROM article_reasons").fetchall():
    print(" ", r)

print("Distinct act_id in articles:")
for r in c.execute("SELECT DISTINCT act_id FROM articles WHERE act_id LIKE '%admin%' OR act_id = 'A0030055'").fetchall():
    print(" ", r)

