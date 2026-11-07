import sqlite3

conn = sqlite3.connect("data/legal_hub.db")
c = conn.cursor()
c.execute("SELECT id, name, last_modified FROM acts LIMIT 10")
for r in c.fetchall():
    print(r)
conn.close()

