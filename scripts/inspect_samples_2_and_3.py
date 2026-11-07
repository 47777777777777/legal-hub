"""
scripts/inspect_samples_2_and_3.py
"""
import os
import sys
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES_DIR = os.path.join(BASE_DIR, "data", "raw", "lis", "samples")

sys.stdout.reconfigure(encoding='utf-8')

for name in ["sample_2", "sample_3"]:
    path = os.path.join(SAMPLES_DIR, f"{name}.html")
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    print(f"\n{'='*70}")
    print(f"=== {name}.html ({len(html)} bytes) ===")
    
    # Print all text in body
    text = soup.get_text("\n", strip=True)
    lines = [l for l in text.splitlines() if l.strip()]
    print(f"Total lines: {len(lines)}")
    for l in lines[:40]:
        print("  ", l)

    # Tables and links
    tables = soup.find_all("table")
    print(f"Tables count: {len(tables)}")
    for i, t in enumerate(tables):
        print(f"  Table {i} rows: {len(t.find_all('tr'))}")
        for r in t.find_all("tr")[:5]:
            cells = [c.get_text(" ", strip=True) for c in r.find_all(["th", "td"])]
            print("    Row:", cells)

