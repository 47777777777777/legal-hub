import subprocess, os

# Create directories on remote first
subprocess.run(["ssh", "-o", "BatchMode=yes", "ubuntu@161.33.166.144", "mkdir -p ~/legal-hub/backend/updater ~/legal-hub/config/systemd ~/legal-hub/reports/screenshots ~/legal-hub/data/chlaw"], check=True)

files = [
    "backend/app.py",
    "backend/storage.py",
    "backend/db.py",
    "backend/updater/base.py",
    "backend/updater/runner.py",
    "backend/updater/cli.py",
    "backend/updater/moj.py",
    "backend/updater/lis.py",
    "backend/updater/lawplayer.py",
    "config/sources.yaml",
    "static/index.html",
    "static/js/app.js",
    "scripts/verify_integrity.py",
    "scripts/smoke_ui.py",
]

for f in files:
    local_path = os.path.join(r"c:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub", f)
    remote_path = f"ubuntu@161.33.166.144:~/legal-hub/{f}"
    res = subprocess.run(["scp", "-o", "BatchMode=yes", local_path, remote_path], capture_output=True)
    if res.returncode != 0:
        print(f"Failed {f}: {res.stderr.decode('utf-8', errors='ignore').strip()}")
    else:
        print(f"OK {f}")

print("Running migrations and restarting legal-hub on remote...")
ssh_cmd = (
    "cd ~/legal-hub && "
    "python3 -c \"import backend.db; backend.db.init_database()\" && "
    "sudo systemctl restart legal-hub.service && "
    "python3 -X utf8 scripts/verify_integrity.py"
)
res = subprocess.run(["ssh", "-o", "BatchMode=yes", "ubuntu@161.33.166.144", ssh_cmd], capture_output=True)
print("SSH STDOUT:\n", res.stdout.decode('utf-8', errors='ignore'))
if res.stderr:
    print("SSH STDERR:\n", res.stderr.decode('utf-8', errors='ignore'))
