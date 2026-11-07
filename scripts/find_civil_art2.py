import urllib.request
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) LegalHub/1.0'}

url = "https://lawplayer.com/act/6437d054e800e5f0b930159a"
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, timeout=15) as resp:
    html = resp.read().decode('utf-8')

matches = re.findall(r'href="/article/([a-f0-9]+)"[^>]*>(.*?)</a>', html)
for aid, text in matches:
    clean_text = re.sub(r'<[^>]+>', ' ', text).strip()
    m = re.search(r'第\s*(\d+(?:之\d+)?)\s*條', clean_text)
    if m and m.group(1) == '2':
        print(f"Civil Code Art 2: https://lawplayer.com/article/{aid} ({clean_text})")
        break

