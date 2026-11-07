import urllib.request
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) LegalHub/1.0'}
req = urllib.request.Request('https://lawplayer.com/rss/acts.xml', headers=headers)
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        xml = resp.read().decode('utf-8')
        print("RSS acts length:", len(xml))
        # items contain <title>...</title> and <link>...</link>
        items = re.findall(r'<item>\s*<title>(.*?)</title>\s*<link>(.*?)</link>', xml, re.DOTALL)
        print("Items found:", len(items))
        for t, l in items:
            if "民事訴訟" in t:
                print(f"MATCH: {t.strip()} -> {l.strip()}")
except Exception as e:
    print("error:", e)

