import urllib.request
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) LegalHub/1.0'}
req = urllib.request.Request('https://lawplayer.com/sitemap_index.xml', headers=headers)
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        xml = resp.read().decode('utf-8')
        locs = re.findall(r'<loc>(https://lawplayer\.com/[^<]+)</loc>', xml)
        print("Sitemaps found:", len(locs))
        for loc in locs:
            print(loc)
except Exception as e:
    print("error:", e)

