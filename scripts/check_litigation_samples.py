import urllib.request
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) LegalHub/1.0'}

# Test line 365, 744, 11922
test_urls = [
    "https://lawplayer.com/act/6437d03ee800e5f0b93012f5", # line 365
    "https://lawplayer.com/act/6437d057e800e5f0b930160f", # line 744
    "https://lawplayer.com/act/64afb3b083f8cb11ab8c86e1", # line 11922
    "https://lawplayer.com/act/6437d03ee800e5f0b93012f7",
    "https://lawplayer.com/act/6437d03ee800e5f0b93012f9"
]

for u in test_urls:
    req = urllib.request.Request(u, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode('utf-8')
            m = re.search(r'<title>(.*?)</title>', html)
            print(u, "->", m.group(1).split(" - ")[0] if m else "None")
    except Exception as e:
        print(u, "Error:", e)

