import urllib.request
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) LegalHub/1.0'}

# Test 6260, 6335, 9245
targets = [
    ("6260", "https://lawplayer.com/act/6437d1bde800e5f0b930433e"),
    ("6335", "https://lawplayer.com/act/6437d1c2e800e5f0b93043db"),
    ("9245", "https://lawplayer.com/act/6437d27ee800e5f0b9305bd1"),
    ("538", "https://lawplayer.com/act/6437d04ae800e5f0b930145d")
]

for tag, u in targets:
    req = urllib.request.Request(u, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode('utf-8')
            m = re.search(r'<title>(.*?)</title>', html)
            print(tag, u, "->", m.group(1).split(" - ")[0] if m else "None")
    except Exception as e:
        print(tag, u, "Error:", e)

