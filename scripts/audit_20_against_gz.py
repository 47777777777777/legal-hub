import gzip
import os
import re
from bs4 import BeautifulSoup
import sys
BASE_DIR = r"C:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.lis.parser import parse_full_act_reasons, parse_lis_article_no
GZ_DIR = os.path.join(BASE_DIR, "data", "raw", "lis", "gz")

TEST_ARTICLES = [
    ("admin_procedure_act", "A0030055", "1", "行政程序法 第 1 條"),
    ("admin_procedure_act", "A0030055", "128", "行政程序法 第 128 條"),
    ("criminal_code", "C0000001", "10", "刑法 第 10 條"),
    ("criminal_code", "C0000001", "296-1", "刑法 第 296-1 條"),
    ("civil_code", "B0000001", "15", "民法 第 15 條"),
    ("traffic_act", "K0040012", "12", "道路交通管理處罰條例 第 12 條"),
    ("labor_standards_act", "N0030001", "32", "勞動基準法 第 32 條"),
    ("company_act", "J0080001", "9", "公司法 第 9 條"),
    ("civil_procedure_code", "B0010001", "244", "民事訴訟法 第 244 條"),
    ("criminal_procedure_code", "C0010001", "160", "刑事訴訟法 第 160 條"),
    ("a0030154", "A0030154", "2", "行政訴訟法 第 2 條"),
    ("constitution", "A0000001", "1", "中華民國憲法 第 1 條"),
    ("criminal_code", "C0000001", "5", "刑法 第 5 條"),
    ("criminal_code", "C0000001", "6", "刑法 第 6 條"),
    ("civil_code", "B0000001", "1", "民法 第 1 條"),
    ("labor_standards_act", "N0030001", "2", "勞動基準法 第 2 條"),
    ("company_act", "J0080001", "1", "公司法 第 1 條"),
    ("traffic_act", "K0040012", "1", "道路交通管理處罰條例 第 1 條"),
    ("civil_procedure_code", "B0010001", "1", "民事訴訟法 第 1 條"),
    ("criminal_procedure_code", "C0010001", "1", "刑事訴訟法 第 1 條"),
]

print("=== Audit of 20 Articles directly against raw .gz files ===")
for act_id, pcode, art_no, label in TEST_ARTICLES:
    gz_path = os.path.join(GZ_DIR, f"{pcode}.html.gz")
    if not os.path.exists(gz_path):
        print(f"{label} ({pcode}): GZ file missing!")
        continue
    with gzip.open(gz_path, "rt", encoding="utf-8", errors="ignore") as f:
        html = f.read()
    
    # Parse reasons directly from raw HTML
    reasons = parse_full_act_reasons(html, raw_path=f"data/raw/lis/gz/{pcode}.html.gz", source_url="")
    matching = [r for r in reasons if r.get("article_no") == art_no]
    
    if matching:
        print(f"[DATA FOUND] {label}: {len(matching)} version(s) in raw .gz")
        for m in matching:
            print(f"   Date: {m.get('version_date')}, Reason head (30): {m.get('reason','')[:30]!r}")
    else:
        # Check if article number appears anywhere in the raw html
        has_str = f"第{art_no}條" in html or f"第一百二十八條" in html or f"第一條" in html
        print(f"[NO DATA IN LIS] {label}: 0 versions found in raw .gz (raw html size: {len(html):,} chars, has_str: {has_str})")
