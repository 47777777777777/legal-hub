import sys
import sqlite3
import json

sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('data/legal_hub.db')
cur = conn.cursor()
cur.execute("SELECT table_data, reason FROM article_comparison WHERE act_id='admin_procedure_act' AND article_no='128'")
row = cur.fetchone()
print("Comparison Reason:")
print(row[1])
print("\nTable data:")
print(json.loads(row[0] or '[]'))

