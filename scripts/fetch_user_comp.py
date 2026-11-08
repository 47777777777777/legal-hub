import sys
import urllib.request
import os
import gzip
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

url = "https://lis.ly.gov.tw/lglawc/lawsingle?00131F01CA74000000000000000005A00000000C00FFFFFD00^01830109123000^00000000000"
out_path = "data/raw/lis/samples/user_apa_128_comp.html"
os.makedirs(os.path.dirname(out_path), exist_ok=True)

req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
try:
    with urllib.request.urlopen(req) as resp:
        content = resp.read()
    with open(out_path, "wb") as f:
        f.write(content)
    print(f"Successfully fetched {len(content)} bytes to {out_path}")
except Exception as e:
    print(f"Error fetching URL: {e}")
    sys.exit(1)

html_text = content.decode('utf-8', errors='ignore')
print(f"HTML text length: {len(html_text)}")
soup = BeautifulSoup(html_text, 'html.parser')

# Find explanation / description / 說明
tables = soup.find_all('table')
print(f"Found {len(tables)} tables")
for idx, t in enumerate(tables):
    txt = t.get_text()
    if '說明' in txt or '新證據' in txt or '第一百二十八條' in txt:
        print(f"\n--- Table {idx} snippet ---")
        print(txt[:300].replace('\n', ' '))

