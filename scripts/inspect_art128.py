import os
import re
from bs4 import BeautifulSoup

# 1. Inspect sample_128.html (Single article LIS page)
p1 = os.path.join("data", "raw", "lis", "sample_128.html")
if os.path.exists(p1):
    with open(p1, "r", encoding="utf-8", errors="ignore") as f:
        html1 = f.read()
    print("=== sample_128.html content search ===")
    soup1 = BeautifulSoup(html1, "html.parser")
    # find date labels and reasons
    text1 = soup1.get_text()
    for m in re.finditer(r"(109\d{4}|110\d{4})", html1):
        start = max(0, m.start() - 100)
        end = min(len(html1), m.end() + 200)
        print(f"Match at {m.start()}:\n{html1[start:end]}\n---")

# 2. Inspect comparisons folder
comp_dir = os.path.join("data", "raw", "lis", "comparisons")
for fname in sorted(os.listdir(comp_dir)):
    if fname.endswith(".html"):
        fp = os.path.join(comp_dir, fname)
        with open(fp, "r", encoding="utf-8", errors="ignore") as f:
            h = f.read()
        if "128" in h or "一百二十八" in h:
            print(f"\n=== Found Art 128 in {fname} ===")
            soup = BeautifulSoup(h, "html.parser")
            # Print table headers and content around 128
            tables = soup.find_all("table")
            for t_idx, t in enumerate(tables):
                t_text = t.get_text()
                if "一百二十八" in t_text or "128" in t_text:
                    print(f"Table {t_idx} has 128. Preview:")
                    for tr in t.find_all("tr")[:6]:
                        print("TR:", [td.get_text(strip=True) for td in tr.find_all(["td", "th"])])

