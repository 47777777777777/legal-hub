import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REMOTE = "ubuntu@161.33.166.144"
REMOTE_PATH = "~/legal-hub"

def run_cmd(cmd, desc):
    print(f"\n--- {desc} ---")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
    print("STDOUT:\n", res.stdout)
    if res.stderr:
        print("STDERR:\n", res.stderr)
    if res.returncode != 0:
        print(f"FAILED (code {res.returncode})")
        return False
    return True

def main():
    print("=== Deploying Prompt 3E / Part 0 to Remote Server ===")
    
    # 1. Sync backend and static files
    files_to_sync = [
        "backend/db.py",
        "backend/models.py",
        "backend/storage.py",
        "backend/lis/parser.py",
        "static/index.html",
        "static/js/app.js",
        "scripts/verify_integrity.py",
        "scripts/import_lis_data.py",
        "scripts/smoke_ui.py",
        "data/lis_export.json"
    ]
    
    for f in files_to_sync:
        local_f = os.path.join(BASE_DIR, f).replace("\\", "/")
        remote_dest = f"{REMOTE}:{REMOTE_PATH}/{f}"
        remote_dir = os.path.dirname(f"{REMOTE_PATH}/{f}")
        # ensure dir exists
        subprocess.run(f'ssh -o StrictHostKeyChecking=no {REMOTE} "mkdir -p {remote_dir}"', shell=True)
        cmd = f'scp -o StrictHostKeyChecking=no "{local_f}" {remote_dest}'
        if not run_cmd(cmd, f"SCP {f}"):
            print("Failed to sync file, aborting.")
            return

    # 2. Sync data/raw/lis
    print("\n--- Syncing data/raw/lis directory ---")
    local_raw_lis = os.path.join(BASE_DIR, "data", "raw", "lis").replace("\\", "/")
    run_cmd(f'ssh -o StrictHostKeyChecking=no {REMOTE} "mkdir -p {REMOTE_PATH}/data/raw/lis"', "Create remote raw lis dir")
    run_cmd(f'scp -r -o StrictHostKeyChecking=no "{local_raw_lis}/." {REMOTE}:{REMOTE_PATH}/data/raw/lis/', "SCP raw lis dir")

    # 3. Remote import LIS data (UPSERT)
    run_cmd(f'ssh -o StrictHostKeyChecking=no {REMOTE} "cd {REMOTE_PATH} && python3 scripts/import_lis_data.py"', "Remote import_lis_data.py")

    # 4. Remote verify_integrity.py
    run_cmd(f'ssh -o StrictHostKeyChecking=no {REMOTE} "cd {REMOTE_PATH} && python3 scripts/verify_integrity.py"', "Remote verify_integrity.py")

    # 5. Restart service
    run_cmd(f'ssh -o StrictHostKeyChecking=no {REMOTE} "sudo systemctl restart legal-hub.service"', "Restart service")

    # 6. Remote smoke UI
    run_cmd(f'ssh -o StrictHostKeyChecking=no {REMOTE} "cd {REMOTE_PATH} && python3 scripts/smoke_ui.py"', "Remote smoke_ui.py")

if __name__ == "__main__":
    main()

