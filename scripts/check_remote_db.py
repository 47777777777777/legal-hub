import subprocess

ssh_cmd = "python3 -c \"import sqlite3; conn = sqlite3.connect('/home/ubuntu/legal-hub/data/legal_hub.db'); cur = conn.cursor(); cur.execute('SELECT name FROM sqlite_master WHERE type=\\'table\\''); print([r[0] for r in cur.fetchall()])\""
res = subprocess.run(["ssh", "-o", "BatchMode=yes", "ubuntu@161.33.166.144", ssh_cmd], capture_output=True, text=True)
print("STDOUT:", res.stdout)
print("STDERR:", res.stderr)

