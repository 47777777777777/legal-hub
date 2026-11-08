import json
import sqlite3

conn = sqlite3.connect("data/legal_hub.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

with open("data/ChLaw.json", "r", encoding="utf-8-sig") as f:
    chlaw = json.load(f)

first_law = chlaw["Laws"][0]
print("ChLaw[0] keys:", list(first_law.keys()))
print("ChLaw[0] LawName:", first_law.get("LawName"))
print("ChLaw[0] LawURL:", first_law.get("LawURL"))

cur.execute("SELECT id, name, pcode FROM acts WHERE name = ?", (first_law.get("LawName"),))
row = cur.fetchone()
print("DB row:", dict(row) if row else None)

