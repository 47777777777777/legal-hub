import urllib.request
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) LegalHub/1.0'}

req = urllib.request.Request("https://lawplayer.com/article-1-sitemap.xml", headers=headers)
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        content = resp.read().decode('utf-8')
        locs = re.findall(r'<loc>(https://lawplayer\.com/article/[^<]+)</loc>', content)
        print(f"Total article URLs in article-1-sitemap.xml: {len(locs)}")
        for l in locs[:5]:
            print(" ", l)
except Exception as e:
    print("Error:", e)

