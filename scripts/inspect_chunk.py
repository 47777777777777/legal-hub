import urllib.request
import re

url = 'https://lawplayer.com/_next/static/chunks/app/(tw)/act/%5Bid%5D/page-7f92a39f.js'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        content = resp.read().decode('utf-8', errors='ignore')
        print('JS Length:', len(content))
        # Look for fetch or api calls
        fetches = set(re.findall(r'fetch\([`\'"]([^`\'"]+)[`\'"]\)', content))
        print('Fetches:', fetches)
        urls = set(re.findall(r'/api/[a-zA-Z0-9_/-]+', content))
        print('API paths in chunk:', urls)
        keys = set(re.findall(r'[a-zA-Z0-9_]+(?=:)', content))
        interesting = [k for k in keys if any(x in k.lower() for x in ['article', 'insight', 'faq', 'knowledge', 'flowchart'])]
        print('Interesting keywords:', interesting[:30])
except Exception as e:
    print('Error:', e)
