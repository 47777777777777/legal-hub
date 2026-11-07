import sys
import json
import os
import re
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

sys.stdout.reconfigure(encoding='utf-8')

from backend.lis.parser import parse_full_act_reasons

s1_path = os.path.join("data", "raw", "lis", "samples", "sample_1.html")
with open(s1_path, "r", encoding="utf-8", errors="ignore") as f:
    raw_html = f.read()

lis_arts = parse_full_act_reasons(raw_html)

versions_per_art = {}
for a in lis_arts:
    no = a['article_no']
    if no not in versions_per_art:
        versions_per_art[no] = []
    versions_per_art[no].append(a)

lis_art_nos = set(versions_per_art.keys())

db_path = os.path.join("data", "legal_hub.db")
conn = sqlite3.connect(db_path)
moj_art_rows = conn.execute("SELECT article_no FROM articles WHERE act_id='admin_procedure_act'").fetchall()
moj_art_nos = set(r[0] for r in moj_art_rows)

print("=== 行政程序法完整切分試跑 (只讀、尚不入庫) ===")
print(f"LIS 解析出的不重複條次數: {len(lis_art_nos)}")
print(f"MOJ 資料庫現行條次數: {len(moj_art_nos)}")
print(f"LIS 總版本記錄數 (條次 x 歷史版本): {len(lis_arts)}")

moj_only = moj_art_nos - lis_art_nos
lis_only = lis_art_nos - moj_art_nos
print(f"\nMOJ 有但 LIS 無: {sorted(list(moj_only), key=lambda x: int(x.split('-')[0]))}")
print(f"LIS 有但 MOJ 無: {sorted(list(lis_only), key=lambda x: int(x.split('-')[0]))}")

ver_counts = {}
for no, v_list in versions_per_art.items():
    cnt = len(v_list)
    ver_counts[cnt] = ver_counts.get(cnt, 0) + 1

print("\n=== 版本數分佈 ===")
for cnt in sorted(ver_counts.keys()):
    print(f"  {cnt} 個版本的條文數: {ver_counts[cnt]} 條")

multi = {no: len(v) for no, v in versions_per_art.items() if len(v) > 1}
print(f"\n多版本條文清單 ({len(multi)} 條):")
for no in sorted(multi.keys(), key=lambda x: int(x.split('-')[0])):
    v_dates = [v['version_date'] + ' ' + v['action_type'] for v in versions_per_art[no]]
    print(f"  第 {no} 條 ({len(v_dates)} 版): {', '.join(v_dates)}")
