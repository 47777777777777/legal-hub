import subprocess

cmd = """
cd ~/legal-hub
python3 -c "
import traceback
from backend.storage import LegalStorage
s = LegalStorage('data/acts')
try:
    act = s.get_act('civil_procedure_code')
    print('ACT ARTICLES:', len(act.get('articles', [])))
except Exception as e:
    traceback.print_exc()
"
"""
res = subprocess.run(["ssh", "-o", "BatchMode=yes", "ubuntu@161.33.166.144", cmd], capture_output=True, text=True)
print("STDOUT:\n", res.stdout)
print("STDERR:\n", res.stderr)

