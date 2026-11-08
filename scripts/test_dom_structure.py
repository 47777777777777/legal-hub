import gzip
import sys
from bs4 import BeautifulSoup

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

gz_path = "data/raw/lis/gz/B0000005.html.gz"
with gzip.open(gz_path, "rt", encoding="utf-8", errors="ignore") as f:
    soup = BeautifulSoup(f.read(), "html.parser")

for af in soup.find_all("font", class_="artino"):
    art_txt = af.get_text(strip=True)
    if "六" in art_txt:
        tbl = af.find_parent("table")
        print(f"Article table: {art_txt}")
        for tr in tbl.find_all("tr", recursive=False):
            # check upddate
            upd = tr.find("font", class_="upddate")
            th = tr.find("td", class_="artiupd_TH_2")
            rs = tr.find("td", class_="artiupd_RS_2")
            if upd:
                print("  UPDDATE:", repr(upd.get_text(strip=True)))
            if th:
                print("  CONTENT:", repr(th.get_text(separator="\n", strip=True)[:40]))
            if rs:
                print("  REASON: ", repr(rs.get_text(separator="\n", strip=True)[:40]))

