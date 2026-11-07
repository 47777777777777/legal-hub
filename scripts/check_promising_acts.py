import urllib.request
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) LegalHub/1.0'}

# Test line 71, 115, 486, 488, 622, 643, 767, 2805
targets = [
    ("71", "https://lawplayer.com/act/6437d02be800e5f0b930106c"),
    ("115", "https://lawplayer.com/act/6437d02ee800e5f0b93010e7"),
    ("486", "https://lawplayer.com/act/6437d046e800e5f0b93013f3"),
    ("488", "https://lawplayer.com/act/6437d046e800e5f0b93013f7"),
    ("622", "https://lawplayer.com/act/6437d04fe800e5f0b9301510"),
    ("643", "https://lawplayer.com/act/6437d050e800e5f0b930153c"),
    ("767", "https://lawplayer.com/act/6437d059e800e5f0b9301640"),
    ("2805", "https://lawplayer.com/act/6437d0dde800e5f0b93026fa")
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

