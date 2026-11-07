import urllib.request
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) LegalHub/1.0'}

# Test lines 778 to 790
candidates = [
    "6437d05ae800e5f0b9301658",
    "6437d05ae800e5f0b930165a",
    "6437d05ae800e5f0b930165c",
    "6437d05ae800e5f0b930165e",
    "6437d05ae800e5f0b9301661",
    "6437d05ae800e5f0b9301663",
    "6437d05ae800e5f0b9301665",
    "6437d05ae800e5f0b9301667",
    "6437d05ae800e5f0b9301669",
    "6437d05ae800e5f0b930166b"
]

for cid in candidates:
    u = f"https://lawplayer.com/act/{cid}"
    req = urllib.request.Request(u, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode('utf-8')
            m = re.search(r'<title>(.*?)</title>', html)
            print(cid, "->", m.group(1).split(" - ")[0] if m else "None")
    except Exception as e:
        print(cid, "Error:", e)

