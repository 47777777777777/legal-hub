"""
scripts/inspect_lis_samples.py

Deeply analyzes the 3 LIS sample HTML pages:
- Identifies which article of Administrative Procedure Act (行政程序法) each sample is.
- Extracts all visible section headings, text blocks, and table headers.
- Analyzes version switching mechanism and URL structure.
"""

import os
import sys
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES_DIR = os.path.join(BASE_DIR, "data", "raw", "lis", "samples")

sys.stdout.reconfigure(encoding='utf-8')

for name in ["sample_1", "sample_2", "sample_3"]:
    path = os.path.join(SAMPLES_DIR, f"{name}.html")
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    title = soup.find("title")
    title_text = title.get_text(strip=True) if title else ""

    print(f"\n{'='*70}")
    print(f"=== File: {name}.html ({len(html)} bytes) ===")
    print(f"Page Title: {title_text}")

    # Look for text matching "行政程序法" and "條"
    print("\n--- Key text findings ---")
    body_text = soup.get_text("\n", strip=True)
    for line in body_text.splitlines():
        if any(kw in line for kw in ["行政程序法", "第", "條", "制定", "修正", "理由", "對照"]):
            if len(line) < 100:
                print("  ", line)

    # Inspect tables
    tables = soup.find_all("table")
    print(f"\nTotal tables found: {len(tables)}")
    for i, t in enumerate(tables[:5]):
        rows = t.find_all("tr")
        print(f"  Table {i}: {len(rows)} rows, class='{t.get('class')}'")
        if rows:
            headers = [td.get_text(" ", strip=True) for td in rows[0].find_all(["th", "td"])]
            print(f"    Header/Row 0: {headers[:5]}")

