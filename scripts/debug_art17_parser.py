import gzip
import sys
from bs4 import BeautifulSoup

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

gz_file = "data/raw/lis/gz/A0040012.html.gz"
with gzip.open(gz_file, "rt", encoding="utf-8", errors="ignore") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")
for tbl in soup.find_all("table"):
    txt = tbl.get_text()
    if "第十七條" in txt and "0871009" in txt:
        print("Found table for 第十七條:")
        print("--- Table text ---")
        print(tbl.get_text(separator="\n", strip=True)[:1500])
        print("--- End Table text ---")
        break
