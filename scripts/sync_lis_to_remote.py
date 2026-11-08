"""
scripts/sync_lis_to_remote.py

Safely exports LIS tables (article_reasons, article_comparison, pending_lis, update_runs, update_changes)
to a JSON payload, transfers to remote host via SCP, and applies atomic UPSERT on remote DB
without whole-database file overwrite.
"""

import os
import sys
import json
import sqlite3
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "legal_hub.db")
PAYLOAD_PATH = os.path.join(BASE_DIR, "data", "lis_sync_payload.json")

def export_lis_payload(act_ids=None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if act_ids:
        placeholders = ",".join("?" for _ in act_ids)
        reasons = [dict(r) for r in cur.execute(f"SELECT * FROM article_reasons WHERE act_id IN ({placeholders})", act_ids).fetchall()]
        versions = [dict(r) for r in cur.execute(f"SELECT * FROM article_versions WHERE act_id IN ({placeholders})", act_ids).fetchall()]
        attempts = [dict(r) for r in cur.execute(f"SELECT * FROM source_attempts WHERE act_id IN ({placeholders})", act_ids).fetchall()]
        comps = [dict(r) for r in cur.execute(f"SELECT * FROM article_comparison WHERE act_id IN ({placeholders})", act_ids).fetchall()]
    else:
        reasons = [dict(r) for r in cur.execute("SELECT * FROM article_reasons").fetchall()]
        versions = [dict(r) for r in cur.execute("SELECT * FROM article_versions").fetchall()]
        attempts = [dict(r) for r in cur.execute("SELECT * FROM source_attempts").fetchall()]
        comps = [dict(r) for r in cur.execute("SELECT * FROM article_comparison").fetchall()]

    pending = [dict(r) for r in cur.execute("SELECT * FROM pending_lis").fetchall()]
    runs = [dict(r) for r in cur.execute("SELECT * FROM update_runs WHERE source = 'lis'").fetchall()]
    changes = [dict(r) for r in cur.execute("SELECT * FROM update_changes WHERE source = 'lis'").fetchall()]
    conn.close()

    payload = {
        "article_reasons": reasons,
        "article_versions": versions,
        "source_attempts": attempts,
        "article_comparison": comps,
        "pending_lis": pending,
        "update_runs": runs,
        "update_changes": changes,
        "exported_at": "2026-11-08T15:40:00"
    }

    with open(PAYLOAD_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Exported LIS payload to {PAYLOAD_PATH}:")
    print(f"  article_reasons:    {len(reasons)} rows")
    print(f"  article_versions:   {len(versions)} rows")
    print(f"  source_attempts:    {len(attempts)} rows")
    print(f"  article_comparison: {len(comps)} rows")
    print(f"  pending_lis:        {len(pending)} rows")
    print(f"  update_runs:        {len(runs)} rows")
    print(f"  update_changes:     {len(changes)} rows")
    return payload

def main():
    print("=== Step 1: Exporting local LIS tables ===")
    export_lis_payload()

    print("\n=== Step 2: Transferring payload to remote via SCP ===")
    remote_dest = "ubuntu@161.33.166.144:~/legal-hub/data/lis_sync_payload.json"
    res = subprocess.run(["scp", "-o", "BatchMode=yes", PAYLOAD_PATH, remote_dest], capture_output=True)
    if res.returncode != 0:
        print(f"SCP failed: {res.stderr.decode('utf-8', errors='ignore')}")
        sys.exit(1)
    print("SCP transfer OK.")

    print("\n=== Step 3: Executing remote UPSERT import script ===")
    ssh_cmd = (
        "cd ~/legal-hub && "
        "python3 scripts/import_lis_payload.py"
    )
    res = subprocess.run(["ssh", "-o", "BatchMode=yes", "ubuntu@161.33.166.144", ssh_cmd], capture_output=True)
    print("Remote STDOUT:\n", res.stdout.decode("utf-8", errors="ignore"))
    if res.stderr:
        print("Remote STDERR:\n", res.stderr.decode("utf-8", errors="ignore"))

if __name__ == "__main__":
    main()

