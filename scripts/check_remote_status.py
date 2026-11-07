import subprocess

cmd = [
    "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
    "ubuntu@161.33.166.144",
    "cd ~/legal-hub && python3 -c 'from backend.storage import LegalStorage; s = LegalStorage(); print(s.get_literature_stats())'"
]
res = subprocess.run(cmd, capture_output=True, text=True)
print("STDOUT:", res.stdout)
print("STDERR:", res.stderr)
