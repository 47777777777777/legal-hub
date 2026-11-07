import urllib.request
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) LegalHub/1.0'}

url = "https://lawplayer.com/act/6437d054e800e5f0b93015aa"
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, timeout=15) as resp:
    html = resp.read().decode('utf-8')

# Find article links
# Check common patterns
# pattern: href="/article/([a-f0-9]+)"
matches = re.findall(r'href="/article/([a-f0-9]+)"[^>]*>(.*?)</a>', html)
print(f"Total article matches: {len(matches)}")
target_articles = {}
for aid, text in matches:
    clean_text = re.sub(r'<[^>]+>', ' ', text).strip()
    # Check if contains article number like 第 1 條, 第 244 條, 第 277 條
    m = re.search(r'第\s*(\d+(?:之\d+)?)\s*條', clean_text)
    if m:
        no = m.group(1)
        if no in ['1', '244', '277']:
            target_articles[no] = (aid, clean_text)

print("Found target articles in Civil Procedure Code:")
for no, (aid, txt) in target_articles.items():
    print(f"  Art {no}: https://lawplayer.com/article/{aid} ({txt})")

