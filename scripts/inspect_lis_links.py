"""
scripts/inspect_lis_links.py
"""
import os
import sys
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES_DIR = os.path.join(BASE_DIR, "data", "raw", "lis", "samples")

sys.stdout.reconfigure(encoding='utf-8')

for name in ["sample_1", "sample_2", "sample_3", "lglawkm_entry"]:
    path = os.path.join(SAMPLES_DIR, f"{name}.html")
    with open(path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    print(f"\n{'='*70}\nLinks in {name}:")
    links = soup.find_all("a")
    print(f"Total links: {len(links)}")
    for a in links[:25]:
        href = a.get("href", "")
        txt = a.get_text(" ", strip=True)
        if "lawsingle" in href or "lglawkm" in href or "javascript" in href:
            print(f"  [{txt[:25]}] -> {href}")

