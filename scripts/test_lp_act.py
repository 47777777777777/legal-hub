import urllib.request
import re
import json

act_url = "https://lawplayer.com/act/6437d05ae800e5f0b9301656"
req = urllib.request.Request(act_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) LegalHub/1.0"})
with urllib.request.urlopen(req, timeout=15) as resp:
    html = resp.read().decode("utf-8")

# Extract article items: href="/article/(...)"<b>第 X 條</b>TITLE</a>
pattern = r'href="/article/([a-f0-9]+)"><b>第\s*([^<]+)\s*條</b>([^<]*)</a>'
matches = re.findall(pattern, html)
print(f"Extracted {len(matches)} articles from LawPlayer Criminal Code!")
for m in matches[:10]:
    print(f"Art {m[1].strip()}: ID={m[0]}, Title={m[2].strip()}")

