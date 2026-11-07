import xml.etree.ElementTree as ET
import urllib.request
import re
import sys
import os

sys.stdout.reconfigure(encoding="utf-8")

# Let's inspect the first 20 act URLs from act-1-sitemap.xml
tree = ET.parse("data/raw/lawplayer/act-1-sitemap.xml")
root = tree.getroot()
urls = []
for child in root:
    loc = child.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
    if loc is not None and loc.text:
        urls.append(loc.text)

print(f"act-1-sitemap.xml has {len(urls)} act URLs.")
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) LegalHub/1.0'}

for u in urls[:10]:
    try:
        req = urllib.request.Request(u, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode('utf-8')
            m = re.search(r'<title>(.*?)</title>', html)
            title = m.group(1).split(" - ")[0].strip() if m else "Unknown"
            print(f"{u} -> {title}")
    except Exception as e:
        print(f"{u} -> Error {e}")

