import urllib.request
import ssl
import os
from bs4 import BeautifulSoup

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

OUT_DIR = "data/raw/lis/comparisons"
os.makedirs(OUT_DIR, exist_ok=True)

# 8 dates of APA (01830)
dates = ['0880115', '0891208', '0900605', '0901228', '0941206', '1020430', '1041211', '1091230']

for d in dates:
    url = f"https://lis.ly.gov.tw/lglawc/lawsingle?001D18E6E752000000000000000005A00000000C00FFFFFD00^01830{d}00^00000000000"
    req = urllib.request.Request(url, headers={'User-Agent': 'LegalHubPersonal/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            raw_bytes = resp.read()
            html = raw_bytes.decode('big5', errors='replace')
            soup = BeautifulSoup(html, 'html.parser')
            has_table = any('版本條文' in tbl.get_text() for tbl in soup.find_all('table'))
            out_file = os.path.join(OUT_DIR, f"comp_{d}.html")
            with open(out_file, "wb") as f:
                f.write(raw_bytes)
            print(f"Date {d}: len={len(html)}, has_table={has_table}, saved to {out_file}")
    except Exception as e:
        print(f"Date {d} error:", e)

