import os
import sys
import time
import json
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from scripts.lis_crawler_pipeline import LisCrawler, NO_FULLPAGE_CSV

# Initialize no_fullpage.csv header if not exists
if not os.path.exists(NO_FULLPAGE_CSV):
    with open(NO_FULLPAGE_CSV, "w", encoding="utf-8") as f:
        f.write("act_id,pcode,law_name,reason\n")

pilot_acts = [
    ("民法", "civil_code", "B0000001"),
    ("行政程序法", "admin_procedure_act", "A0030109"),
    ("國家賠償法", "state_compensation_law", "I0020004"),
    ("營業秘密法", "trade_secrets_act", "J0080028"),
    ("涉外民事法律適用法", "act_governing_choice_of_law_in_civil_matters", "B0000007"),
    ("消費者保護法", "consumer_protection_act", "J0170001"),
    ("中華民國憲法", "constitution", "A0000001"),
    ("動員戡亂時期臨時條款", "a0000005", "A0000005"),
    ("司法院釋字第七四八號解釋施行法", "a0000104", "B0000017"),
    ("勞動基準法", "labor_standards_act", "N0030001")
]

crawler = LisCrawler()
results = []

print("=== STEP 1-2: PILOT RUN FOR 10 REPRESENTATIVE ACTS ===")
for law_name, act_id, pcode in pilot_acts:
    print(f"\nCrawling '{law_name}' ({act_id}, {pcode})...")
    res = crawler.crawl_act(law_name, act_id, pcode)
    results.append(res)
    print(f"  Result: success={res['success']}, reqs={res['req_count']}, duration={round(res['duration'], 2)}s, raw_size={res.get('raw_size', 0):,}B, gz_size={res.get('gz_size', 0):,}B, reasons={res.get('reasons_count', 0)}")
    if not res["success"]:
        print(f"  Note: Recorded in {NO_FULLPAGE_CSV}")

print("\n=== PILOT 10 SUMMARY TABLE ===")
print(f"{'法規名稱':<20} | {'Act ID':<22} | {'請求數':<6} | {'原始大小(B)':<12} | {'壓縮大小(B)':<12} | {'耗時(s)':<8} | {'理由筆數':<8} | {'狀態'}")
print("-" * 110)
for r in results:
    name = r.get("law_name", "")
    aid = r.get("act_id", "")
    reqs = r.get("req_count", 0)
    raw_s = r.get("raw_size", 0)
    gz_s = r.get("gz_size", 0)
    dur = round(r.get("duration", 0), 2)
    cnt = r.get("reasons_count", 0)
    status = "SUCCESS" if r.get("success") else "NO_FULLPAGE"
    print(f"{name:<20} | {aid:<22} | {reqs:<6} | {raw_s:<12,} | {gz_s:<12,} | {dur:<8} | {cnt:<8} | {status}")

