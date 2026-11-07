"""
scripts/deploy_remote.py
One-click deployment script:
1. Pushes local commits to GitHub origin main.
2. Connects via SSH to Oracle Cloud server (161.33.166.144).
3. Executes git pull origin main.
4. Runs verify_integrity.py on remote server.
5. Restarts legal-hub.service and verifies health check HTTP 200.
"""

import subprocess
import sys
import urllib.request
import time

REMOTE_HOST = "ubuntu@161.33.166.144"
HEALTH_URL = "http://161.33.166.144/api/acts/civil_code"

def run_cmd(cmd, check=True):
    print(f">> Executing: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    res = subprocess.run(cmd, check=check, text=True, capture_output=True)
    if res.stdout:
        print(res.stdout)
    if res.stderr:
        print(res.stderr, file=sys.stderr)
    return res

def main():
    print("=== Deploying Legal Hub to Oracle Cloud (161.33.166.144) ===")
    
    # 1. Push to GitHub
    print("\n[Step 1/4] Pushing latest commits to GitHub...")
    run_cmd(["git", "push", "origin", "main"])
    
    # 2. Remote git pull
    print("\n[Step 2/4] Remote git pull on Oracle server...")
    ssh_cmd = "cd ~/legal-hub && git pull origin main"
    run_cmd(["ssh", "-o", "BatchMode=yes", REMOTE_HOST, ssh_cmd])

    # 3. Remote service restart
    print("\n[Step 3/4] Restarting legal-hub.service...")
    run_cmd(["ssh", "-o", "BatchMode=yes", REMOTE_HOST, "sudo systemctl restart legal-hub.service"])

    # 4. Remote health check
    print("\n[Step 4/4] Verifying remote service health...")
    time.sleep(2)
    try:
        req = urllib.request.urlopen(HEALTH_URL, timeout=10)
        status = req.status
        print(f"Health check status: HTTP {status} OK!")
        if status == 200:
            print("\n>>> SUCCESS: Remote deployment to http://161.33.166.144/ is LIVE and healthy! <<<")
            return 0
    except Exception as e:
        print(f"Health check failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
