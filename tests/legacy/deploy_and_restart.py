import subprocess, os

files_to_sync = [
    "static/index.html",
    "static/js/app.js",
    "static/css/style.css",
    "backend/app.py",
    "backend/storage.py",
    "data/all_authentic_lp_titles.json",
    "data/acts/civil_code.json",
    "data/acts/criminal_code.json",
    "scripts/apply_lp_titles.py",
]

for f in files_to_sync:
    local_path = os.path.join(r"c:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub", f)
    remote_path = f"ubuntu@161.33.166.144:~/legal-hub/{f}"
    print(f"Syncing {f}...")
    res = subprocess.run(["scp", "-o", "BatchMode=yes", local_path, remote_path], capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Failed {f}: {res.stderr}")
    else:
        print(f"OK {f}")

print("Applying LP titles and restarting legal-hub on remote...")
ssh_cmd = (
    "cd ~/legal-hub && "
    "python3 scripts/apply_lp_titles.py && "
    "sudo systemctl restart legal-hub.service && "
    "sudo systemctl restart apache2"
)
res = subprocess.run(["ssh", "-o", "BatchMode=yes", "ubuntu@161.33.166.144", ssh_cmd], capture_output=True, text=True)
print("SSH STDOUT:\n", res.stdout)
print("SSH STDERR:\n", res.stderr)

