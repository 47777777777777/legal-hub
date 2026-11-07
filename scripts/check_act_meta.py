import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

# Let's inspect an act page HTML or RSC
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) LegalHub/1.0'}
sample_ids = [
    "6437d027e800e5f0b9300e5d",
    "6437d027e800e5f0b9300e60",
    "6437d027e800e5f0b9300e62"
]
for act_id in sample_ids:
    url = f"https://lawplayer.com/act/{act_id}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8')
            import re
            title_m = re.search(r'<title>(.*?)</title>', html)
            print(act_id, "->", title_m.group(1) if title_m else "None")
    except Exception as e:
        print(act_id, "Error:", e)
