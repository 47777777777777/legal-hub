import os
import sys
import json
import sqlite3
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "legal_hub.db")
GZ_DIR = os.path.join(BASE_DIR, "data", "raw", "lis", "gz")
REMOTE_HOST = "ubuntu@161.33.166.144"
REMOTE_APP_DIR = "legal-hub"

def run_ssh(cmd):
    p = subprocess.run(["ssh", "-o", "StrictHostKeyChecking=no", REMOTE_HOST, cmd], capture_output=True, text=True, encoding="utf-8")
    if p.returncode != 0 and p.stderr:
        print(f"SSH Warning/Error: {p.stderr.strip()}")
    return p.stdout.strip()

def run_scp(local_path, remote_path):
    p = subprocess.run(["scp", "-o", "StrictHostKeyChecking=no", "-r", local_path, f"{REMOTE_HOST}:{remote_path}"], capture_output=True, text=True)
    if p.returncode != 0 and p.stderr:
        print(f"SCP Error: {p.stderr.strip()}")
    return p.returncode == 0

def main():
    print("=== Step 1: Query Local Counts ===")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT count(*), count(DISTINCT act_id||'|'||article_no) FROM article_reasons")
    local_reasons, local_dist = cur.fetchone()
    cur.execute("SELECT count(*) FROM source_attempts WHERE source='lis'")
    local_attempts = cur.fetchone()[0]
    print(f"Local: article_reasons={local_reasons} (distinct={local_dist}), source_attempts={local_attempts}")

    print("\n=== Step 2: Query Remote Counts Before Sync ===")
    query_cmd = """python3 -c "import sqlite3; conn=sqlite3.connect('legal-hub/data/legal_hub.db'); cur=conn.cursor(); cur.execute('SELECT count(*) FROM article_reasons'); print('Count:', cur.fetchone()[0])" """
    remote_before = run_ssh(query_cmd)
    print(f"Remote Before: {remote_before}")

    print("\n=== Step 3: Export Local Tier 1 Data Payload ===")
    cur.execute("""
        SELECT act_id, article_no, version_date, action_type, reason, source, source_url, fetched_at, raw_path, 
               date_label_raw, date_raw, article_no_at_the_time, source_mode 
        FROM article_reasons
    """)
    reasons_rows = cur.fetchall()
    
    cur.execute("SELECT source, act_id, article_no, status, error_reason, duration_ms, created_at FROM source_attempts")
    attempts_rows = cur.fetchall()

    payload = {
        "reasons": reasons_rows,
        "attempts": attempts_rows
    }
    payload_file = os.path.join(BASE_DIR, "data", "tier1_lis_payload.json")
    with open(payload_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    print(f"Exported payload to {payload_file} ({len(reasons_rows)} reasons, {len(attempts_rows)} attempts)")

    print("\n=== Step 4: Transfer GZ Files and Payload to Remote ===")
    run_ssh(f"mkdir -p {REMOTE_APP_DIR}/data/raw/lis/gz")
    gz_files = [os.path.join(GZ_DIR, f) for f in os.listdir(GZ_DIR) if f.endswith(".gz")]
    for gz in gz_files:
        run_scp(gz, f"{REMOTE_APP_DIR}/data/raw/lis/gz/{os.path.basename(gz)}")
    print(f"Transferred {len(gz_files)} .html.gz files to remote.")

    run_scp(payload_file, f"{REMOTE_APP_DIR}/data/tier1_lis_payload.json")
    print("Transferred payload to remote.")

    print("\n=== Step 5: Execute Ingestion on Remote ===")
    remote_ingest_script = """import sqlite3, json, os

conn = sqlite3.connect('legal-hub/data/legal_hub.db')
cur = conn.cursor()

cur.execute('''
CREATE TABLE IF NOT EXISTS source_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    act_id TEXT NOT NULL,
    article_no TEXT NOT NULL,
    status TEXT NOT NULL,
    error_reason TEXT,
    duration_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
''')

with open('legal-hub/data/tier1_lis_payload.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for row in data['reasons']:
    (act_id, article_no, version_date, action_type, reason, source, source_url, 
     fetched_at, raw_path, date_label_raw, date_raw, article_no_at_the_time, source_mode) = row
    
    # Adjust remote raw_path
    if raw_path:
        base_name = os.path.basename(raw_path)
        remote_raw_path = f"/home/ubuntu/legal-hub/data/raw/lis/gz/{base_name}"
    else:
        remote_raw_path = None

    cur.execute('''
        SELECT id FROM article_reasons 
        WHERE act_id = ? AND article_no = ? AND version_date = ?
    ''', (act_id, article_no, version_date))
    existing = cur.fetchone()
    if existing:
        cur.execute('''
            UPDATE article_reasons 
            SET action_type = ?, reason = ?, source = ?, source_url = ?, fetched_at = ?, raw_path = ?,
                date_label_raw = ?, date_raw = ?, article_no_at_the_time = ?, source_mode = ?
            WHERE id = ?
        ''', (action_type, reason, source, source_url, fetched_at, remote_raw_path,
              date_label_raw, date_raw, article_no_at_the_time, source_mode, existing[0]))
    else:
        cur.execute('''
            INSERT INTO article_reasons (
                act_id, article_no, version_date, action_type, reason, source, source_url, fetched_at, 
                raw_path, date_label_raw, date_raw, article_no_at_the_time, source_mode
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (act_id, article_no, version_date, action_type, reason, source, source_url, fetched_at,
              remote_raw_path, date_label_raw, date_raw, article_no_at_the_time, source_mode))

for row in data['attempts']:
    source, act_id, article_no, status, error_reason, duration_ms, created_at = row
    cur.execute('DELETE FROM source_attempts WHERE act_id = ? AND source = ? AND article_no = ?', (act_id, source, article_no))
    cur.execute('''
        INSERT INTO source_attempts (source, act_id, article_no, status, error_reason, duration_ms, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (source, act_id, article_no, status, error_reason, duration_ms, created_at))

conn.commit()
cur.execute("SELECT count(*), count(DISTINCT act_id||'|'||article_no) FROM article_reasons")
cnt, dist = cur.fetchone()
print(f"Remote Ingestion Completed! article_reasons count: {cnt} (distinct articles: {dist})")
conn.close()
"""
    # Write remote script locally first, then scp and run
    local_script_path = os.path.join(BASE_DIR, "scripts", "remote_apply_tier1.py")
    with open(local_script_path, "w", encoding="utf-8") as f:
        f.write(remote_ingest_script)
    run_scp(local_script_path, f"{REMOTE_APP_DIR}/scripts/remote_apply_tier1.py")
    res = run_ssh(f"python3 {REMOTE_APP_DIR}/scripts/remote_apply_tier1.py")
    print(res)

    print("\n=== Step 6: Restart Remote Backend Service ===")
    run_ssh("sudo systemctl restart legal-hub")
    status = run_ssh("systemctl is-active legal-hub")
    print(f"Remote service status: {status}")

    print("\n=== Step 7: Verify Remote API ===")
    verify_cmd = """python3 -c "import urllib.request, json; res = urllib.request.urlopen('http://127.0.0.1:8080/api/acts/criminal_code/articles/10/panel'); d = json.loads(res.read().decode('utf-8'))['data']['legislative_reasons']; print('Art 10 Reasons Status:', d.get('status'), 'Count:', len(d.get('items', [])))" """
    verify_api = run_ssh(verify_cmd)
    print(f"Remote API Check (Criminal Code Art 10): {verify_api}")

    conn.close()

if __name__ == "__main__":
    main()
