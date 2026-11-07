import sqlite3

conn = sqlite3.connect('data/legal_hub.db')
c = conn.cursor()
tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print('TABLES:', tables)
conn.close()

