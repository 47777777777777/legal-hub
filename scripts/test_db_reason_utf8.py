import sys
import sqlite3

sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('data/legal_hub.db')
cur = conn.cursor()
cur.execute("SELECT act_id, article_no, version_date, reason FROM article_reasons WHERE act_id='criminal_code' AND article_no='296-1'")
row = cur.fetchone()
print("Act:", row[0], "Art:", row[1], "Date:", row[2])
print("Reason:")
print(row[3])

