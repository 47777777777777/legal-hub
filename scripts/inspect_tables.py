import sqlite3

conn = sqlite3.connect(r'C:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub\data\legal_hub.db')
c = conn.cursor()
tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print('Tables:', tables)

for t in tables:
    if 'comp' in t.lower() or 'history' in t.lower() or 'reason' in t.lower() or 'ver' in t.lower():
        cnt = c.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        cols = [r[1] for r in c.execute(f"PRAGMA table_info({t})").fetchall()]
        print(f"Table {t} ({cnt} rows): {cols}")

