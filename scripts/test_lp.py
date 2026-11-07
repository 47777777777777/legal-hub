import urllib.request
import re
import json

url = 'https://lawplayer.com/article/6438e7fee800e5f0b932c8a0'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
with urllib.request.urlopen(req, timeout=10) as resp:
    html = resp.read().decode('utf-8')

# Search for article title, summary, etc.
# Check title tag
title = re.search(r'<title>(.*?)</title>', html)
print("Title:", title.group(1) if title else "None")

# Check meta description
desc = re.search(r'<meta name="description" content="(.*?)"', html)
print("Description:", desc.group(1) if desc else "None")

# Check sections in the html
sections = re.findall(r'<section[^>]*>(.*?)</section>', html, re.DOTALL)
print("Sections count:", len(sections))
for i, s in enumerate(sections[:5]):
    # Strip tags
    text = re.sub(r'<[^>]+>', ' ', s)
    text = ' '.join(text.split())
    print(f"Section {i+1}: {text[:150]}")
