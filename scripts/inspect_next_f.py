import urllib.request
import re

url = 'https://lawplayer.com/act/6437d05ae800e5f0b9301656'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
with urllib.request.urlopen(req, timeout=15) as resp:
    html = resp.read().decode('utf-8')

# Find scripts
scripts = re.findall(r'<script([^>]*)>(.*?)</script>', html, re.DOTALL)
print(f'Total script tags: {len(scripts)}')
for attrs, content in scripts:
    if 'self.__next_f' in content:
        print('Found Next.js App Router streaming payload! Length:', len(content))
        # Print sample of next_f
        sample = content[:300].replace('\n', ' ')
        print('  Sample:', sample)
    elif 'src=' in attrs:
        src = re.search(r'src="([^"]+)"', attrs)
        if src and '_next' in src.group(1):
            # check js bundles
            pass

# Also look for API domain names
domains = set(re.findall(r'https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', html))
print('Domains referenced:', domains)
