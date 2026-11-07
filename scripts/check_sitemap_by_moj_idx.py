import xml.etree.ElementTree as ET
import urllib.request
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
tree = ET.parse("data/raw/lawplayer/act-1-sitemap.xml")
root = tree.getroot()
urls = []
for child in root:
    loc = child.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
    if loc is not None and loc.text:
        urls.append(loc.text)

print(f"Total act URLs: {len(urls)}")

# Check index around 70, 113, 574!
# Let's inspect indices 65 to 75, 108 to 118, 570 to 580
indices_to_check = list(range(65, 75)) + list(range(108, 120)) + list(range(568, 580))
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) LegalHub/1.0'}

for i in indices_to_check:
    u = urls[i]
    try:
        req = urllib.request.Request(u, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode('utf-8')
            m = re.search(r'<title>(.*?)</title>', html)
            name = m.group(1).split(" - ")[0].strip() if m else "Unknown"
            print(f"Index {i}: {u} -> {name}")
    except Exception as e:
        print(f"Index {i}: {u} -> Error {e}")

