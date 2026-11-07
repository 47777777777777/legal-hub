import subprocess

cmd = """
cd ~/legal-hub
python3 -c "
import sqlite3
conn = sqlite3.connect('data/legal_hub.db')
cur = conn.cursor()
for r in cur.execute('SELECT id, pcode, name FROM acts WHERE name LIKE ?', ('%民事訴訟%',)):
    print('ACT:', r)
for r in cur.execute('SELECT act_id, count(*) FROM articles GROUP BY act_id ORDER BY count(*) DESC LIMIT 10'):
    print('TOP ACT ARTICLES:', r)
"
"""
res = subprocess.run(["ssh", "-o", "BatchMode=yes", "ubuntu@161.33.166.144", cmd], capture_output=True)
print("STDOUT:\n", res.stdout.decode('utf-8', errors='ignore'))
if res.stderr:
    print("STDERR:\n", res.stderr.decode('utf-8', errors='ignore'))
