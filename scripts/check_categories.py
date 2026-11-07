import sqlite3

conn = sqlite3.connect('data/legal_hub.db')
c = conn.cursor()
c.execute("SELECT DISTINCT category FROM acts WHERE id IN ('constitution', 'civil_code', 'criminal_code', 'admin_procedure_act')")
print("LAW CATEGORIES:", c.fetchall())

c.execute("SELECT DISTINCT category FROM acts WHERE category LIKE '%命令%' LIMIT 5")
print("ORDER CATEGORIES WITH 命令:", c.fetchall())

# Check how many acts have '法律' or '憲法' or '命令'
c.execute("SELECT count(*) FROM acts WHERE category LIKE '%憲法%'")
print("Acts with 憲法 in category:", c.fetchone()[0])

c.execute("SELECT count(*) FROM acts WHERE category LIKE '%法律%'")
print("Acts with 法律 in category:", c.fetchone()[0])

c.execute("SELECT count(*) FROM acts WHERE category LIKE '%命令%'")
print("Acts with 命令 in category:", c.fetchone()[0])

conn.close()

