import sys
import subprocess

sys.stdout.reconfigure(encoding='utf-8')

cmd = sys.argv[1] if len(sys.argv) > 1 else "uptime"
res = subprocess.run(["ssh", "-o", "StrictHostKeyChecking=no", "ubuntu@161.33.166.144", cmd], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
print("STDOUT:\n", res.stdout)
if res.stderr:
    print("STDERR:\n", res.stderr)
print("Return code:", res.returncode)
