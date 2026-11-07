import os
import subprocess

print("=== Deploying Prompt 3 to Remote Server 161.33.166.144 ===")

# 1. Pull code on remote
print("\n1. Pulling latest git commit on remote...")
res = subprocess.run(["ssh", "-o", "StrictHostKeyChecking=no", "ubuntu@161.33.166.144", "cd ~/legal-hub && git pull origin main"], capture_output=True, text=True)
print("Git pull stdout:\n", res.stdout)
if res.stderr:
    print("Git pull stderr:\n", res.stderr)

# 2. SCP JSONL
print("\n2. Copying data/enrichments_tier1.jsonl to remote...")
local_jsonl = r"c:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub\data\enrichments_tier1.jsonl"
res = subprocess.run(["scp", "-o", "StrictHostKeyChecking=no", local_jsonl, "ubuntu@161.33.166.144:~/legal-hub/data/enrichments_tier1.jsonl"], capture_output=True, text=True)
if res.returncode != 0:
    print("SCP failed:\n", res.stderr)
else:
    print("SCP successful.")

# 3. Import enrichments on remote
print("\n3. Running import_enrichments.py on remote...")
res = subprocess.run(["ssh", "-o", "StrictHostKeyChecking=no", "ubuntu@161.33.166.144", "cd ~/legal-hub && python3 scripts/import_enrichments.py"], capture_output=True, text=True)
print("Remote import stdout:\n", res.stdout)
if res.stderr:
    print("Remote import stderr:\n", res.stderr)

# 4. Run verify_integrity.py on remote
print("\n4. Running verify_integrity.py on remote...")
res = subprocess.run(["ssh", "-o", "StrictHostKeyChecking=no", "ubuntu@161.33.166.144", "cd ~/legal-hub && python3 scripts/verify_integrity.py"], capture_output=True, text=True)
print("Remote verify_integrity stdout:\n", res.stdout)
if res.stderr:
    print("Remote verify_integrity stderr:\n", res.stderr)

# 5. Restart service
print("\n5. Restarting legal-hub.service on remote...")
res = subprocess.run(["ssh", "-o", "StrictHostKeyChecking=no", "ubuntu@161.33.166.144", "sudo systemctl restart legal-hub.service"], capture_output=True, text=True)
print("Service restarted.")

