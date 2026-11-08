import sys
import os
import json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = r"C:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub"
sys.path.insert(0, BASE_DIR)

from scripts.lis_crawler_pipeline import LisCrawler

test_laws = [
    ("消費者保護法", "consumer_protection_act", "J0170001"),
    ("國家賠償法", "state_compensation_law", "I0020004"),
    ("營業秘密法", "trade_secrets_act", "J0080028"),
    ("涉外民事法律適用法", "act_governing_choice_of_law", "B0000007"),
    ("司法院釋字第七四八號解釋施行法", "act_interpretation_748", "B0000008")
]

crawler = LisCrawler()

for name, act_id, pcode in test_laws:
    print(f"\n--- Testing crawl: {name} ({pcode}) ---")
    try:
        res = crawler.crawl_act(name, act_id, pcode)
        print(f"Success: {res.get('success')}, Reasons: {res.get('reasons_count')}, Req count: {res.get('req_count')}, Duration: {round(res.get('duration', 0), 2)}s, GZ size: {res.get('gz_size')}")
        if not res.get("success"):
            print(f"Error: {res.get('error')}")
    except Exception as e:
        print(f"Exception: {e}")

