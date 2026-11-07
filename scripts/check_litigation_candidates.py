import urllib.request
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) LegalHub/1.0'}

# Test 439, 674, 675, 709, 737
candidates = [
    "https://lawplayer.com/act/6437d043e800e5f0b930138f", # line 439
    "https://lawplayer.com/act/6437d052e800e5f0b930157c", # line 674
    "https://lawplayer.com/act/6437d053e800e5f0b930157e", # line 675
    "https://lawplayer.com/act/6437d055e800e5f0b93015c4", # line 709
    "https://lawplayer.com/act/6437d057e800e5f0b9301601"  # line 737
]

for u in candidates:
    req = urllib.request.Request(u, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode('utf-8')
            m = re.search(r'<title>(.*?)</title>', html)
            print(u, "->", m.group(1).split(" - ")[0] if m else "None")
    except Exception as e:
        print(u, "Error:", e)

