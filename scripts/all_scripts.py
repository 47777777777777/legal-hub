import urllib.request
import re

url = 'https://lawplayer.com/act/6437d05ae800e5f0b9301656'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=10) as resp:
    html = resp.read().decode('utf-8', errors='ignore')

all_js = set(re.findall(r'src="(/_next/[^"]+)"', html))
print('Direct script srcs:', len(all_js))
for j in all_js:
    print(' ', j)

