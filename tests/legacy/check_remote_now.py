import subprocess, os

def run_ssh(cmd_str):
    res = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", "ubuntu@161.33.166.144", cmd_str],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        timeout=15
    )
    return res.stdout, res.stderr

results = []
results.append("=== REMOTE static/js/app.js ===")
out, err = run_ssh("grep -n '民法' ~/legal-hub/static/js/app.js | head -n 30")
results.append(out)

results.append("=== REMOTE curl 5000 /api/acts/civil_code ===")
out, err = run_ssh("curl -s http://127.0.0.1:5000/api/acts/civil_code | python3 -c \"import json, sys; d = json.load(sys.stdin); print('Remote Act Name:', d['data']['name']); print([(a['article_no'], a['title']) for a in d['data']['articles'][:5]])\"")
results.append(out)

results.append("=== REMOTE APACHE SITES ===")
out, err = run_ssh("cat /etc/apache2/sites-enabled/* | grep -E 'DocumentRoot|ProxyPass'")
results.append(out)

out_path = r"c:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub\scripts\remote_check_out.txt"
with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(results))
print("DONE")
