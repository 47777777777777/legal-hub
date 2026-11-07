import urllib.request
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) LegalHub/1.0'}

for act_id in ['6437d054e800e5f0b93015aa', '6437d054e800e5f0b93015ac']:
    url = f"https://lawplayer.com/act/{act_id}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as resp:
        html = resp.read().decode('utf-8')
        title_m = re.search(r'<title>(.*?)</title>', html)
        title = title_m.group(1) if title_m else 'No title'
        print(f"{act_id} -> {title}")

