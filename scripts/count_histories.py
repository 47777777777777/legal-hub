import sqlite3

conn = sqlite3.connect('data/legal_hub.db')
c = conn.cursor()
c.execute("SELECT count(*) FROM acts WHERE history_json IS NOT NULL AND history_json != '[]' AND history_json != ''")
print('Acts with history_json:', c.fetchone()[0])
c.execute("SELECT count(*) FROM acts")
print('Total acts:', c.fetchone()[0])
conn.close()

