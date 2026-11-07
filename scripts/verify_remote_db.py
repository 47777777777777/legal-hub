import sqlite3

conn = sqlite3.connect('/home/ubuntu/legal-hub/data/legal_hub.db')
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM literature')
print('Total articles in DB:', c.fetchone()[0])
c.execute('SELECT COUNT(*) FROM literature WHERE author = "林山田"')
print('Articles with 林山田:', c.fetchone()[0])
c.execute('SELECT DISTINCT journal_name, COUNT(*) FROM literature GROUP BY journal_name ORDER BY COUNT(*) DESC')
print('Journals in DB:')
for j, cnt in c.fetchall():
    print(f'  {j}: {cnt} 篇')
