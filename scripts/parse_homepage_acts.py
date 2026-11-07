import urllib.request
import re
import sys

# Force utf-8 stdout
sys.stdout.reconfigure(encoding='utf-8')

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) LegalHub/1.0'}
req = urllib.request.Request('https://lawplayer.com', headers=headers)
with urllib.request.urlopen(req, timeout=10) as resp:
    content = resp.read().decode('utf-8')

matches = re.findall(r'href=["\'](/act/[a-f0-9]+)["\'][^>]*>(.*?)</a>', content, re.DOTALL)
print(f"Total act links on homepage: {len(matches)}")
seen = set()
for href, text in matches:
    clean_text = " ".join(re.sub(r'<[^>]+>', ' ', text).split())
    if href not in seen:
        seen.add(href)
        print(f"{href} -> {clean_text}")
