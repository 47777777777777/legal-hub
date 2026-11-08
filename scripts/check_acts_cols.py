import sqlite3

conn = sqlite3.connect(r'C:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub\data\legal_hub.db')
c = conn.cursor()
cols = [r[1] for r in c.execute("PRAGMA table_info(acts)").fetchall()]
print("Acts cols:", cols)
rows = c.execute("SELECT id, name, pcode FROM acts WHERE id='a0030154' OR pcode='A0030154'").fetchall()
print("Rows:", rows)
rows2 = c.execute("SELECT id, name, pcode FROM acts WHERE name LIKE '%走私%' OR name LIKE '%行政訴訟%'").fetchall()
print("Rows2:", rows2)

