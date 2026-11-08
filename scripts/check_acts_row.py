import sqlite3

conn = sqlite3.connect(r'C:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub\data\legal_hub.db')
c = conn.cursor()
row = c.execute("SELECT act_id, act_name, pcode FROM acts WHERE act_id='a0030154' OR pcode='A0030154'").fetchone()
print("In acts table:", row)
row2 = c.execute("SELECT act_id, act_name, pcode FROM acts WHERE act_name LIKE '%走私%' OR act_name LIKE '%行政訴訟%'").fetchall()
print("Search by name:", row2)

