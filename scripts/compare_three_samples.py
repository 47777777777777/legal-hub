"""
scripts/compare_three_samples.py
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
        soup = BeautifulSoup(f.read(), "html.parser")
    
    print(f"\n{'='*70}\nInspection of {name}:")
    # Find all h1, h2, h3, or specific classes
    for tag in soup.find_all(["h1", "h2", "h3", "font", "span", "td"]):
        txt = tag.get_text(" ", strip=True)
        # Check if there is version or article indicator
        if any(w in txt for w in ["第一百二十八條", "第一條", "版本條文", "修正條文對照表"]):
            if len(txt) < 80:
                print(f"  [{tag.name}.{tag.get('class')}] {txt}")

