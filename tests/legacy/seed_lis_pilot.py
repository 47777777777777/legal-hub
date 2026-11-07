"""
種入 Prompt 3D 三個試點條文 (行政程序法 第 1 條、第 128 條、第 174-1 條)
資料完全萃取自 data/raw/lis/samples/*.html，保證 100% 官方原文逐字入庫。
"""
import os
import sys
import json
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.lis.parser import (
    parse_full_act_reasons,
    parse_comparison_table,
    parse_single_article
)

DB_PATH = os.path.join(BASE_DIR, "data", "legal_hub.db")
SAMPLE_DIR = os.path.join(BASE_DIR, "data", "raw", "lis", "samples")


def seed_pilot():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # 讀取 Sample 1
    s1_path = os.path.join(SAMPLE_DIR, "sample_1.html")
    with open(s1_path, "r", encoding="utf-8", errors="ignore") as f:
        s1_html = f.read()

    # 讀取 Sample 2
    s2_path = os.path.join(SAMPLE_DIR, "sample_2.html")
    with open(s2_path, "r", encoding="utf-8", errors="ignore") as f:
        s2_html = f.read()

    # 讀取 Sample 3
    s3_path = os.path.join(SAMPLE_DIR, "sample_3.html")
    with open(s3_path, "r", encoding="utf-8", errors="ignore") as f:
        s3_html = f.read()

    fetched_at = "2026-11-03"
    act_id = "admin_procedure_act"

    # 1. 解析 Sample 1 全法
    all_arts = parse_full_act_reasons(
        s1_html,
        raw_path=s1_path,
        source_url="https://lis.ly.gov.tw/lglawc/lawsingle?001D18E6E7520000000000000000032000000007000000^01830109123000^00000000000"
    )

    # 僅篩選試點三條：1, 128, 174-1
    target_nos = {"1", "128", "174-1"}
    pilot_arts = [a for a in all_arts if a["article_no"] in target_nos]

    print(f"Parsed {len(pilot_arts)} versions for target articles {target_nos} from Sample 1:")
    for a in pilot_arts:
        print(f"  Art {a['article_no']} ({a['version_date']} {a['action_type']}): reason_len={len(a['reason'])}")
        
        # 寫入 article_reasons
        cur.execute("""
            INSERT OR REPLACE INTO article_reasons (
                act_id, article_no, version_date, action_type, reason, source, source_url, fetched_at, raw_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            act_id, a["article_no"], a["version_date"], a["action_type"],
            a["reason"], a["source"], a["source_url"], fetched_at, s1_path
        ))

        # 寫入 article_versions
        cur.execute("""
            INSERT OR REPLACE INTO article_versions (
                act_id, article_no, version_date, action_type, content, source, source_url, fetched_at, raw_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            act_id, a["article_no"], a["version_date"], a["action_type"],
            a["content"], a["source"], a["source_url"], fetched_at, s1_path
        ))

    # 2. 解析 Sample 2 (第 128 條 1091230 修正對照表)
    comp = parse_comparison_table(
        s2_html,
        raw_path=s2_path,
        source_url="https://lis.ly.gov.tw/lglawc/lawsingle?001D18E6E752000000000000000005A00000000C00FFFFFD00^01830109123000^00000000000"
    )
    if comp and comp.get("article_no"):
        print(f"\nParsed Comparison for Art {comp['article_no']} (version {comp['new_version_date']}):")
        print(f"  Reason: {comp['reason'][:80]}...")
        cur.execute("""
            INSERT OR REPLACE INTO article_comparison (
                act_id, article_no, new_version_date, old_version_date, action_type,
                new_content, old_content, reason, table_data, source, source_url, fetched_at, raw_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            act_id, comp["article_no"], comp["new_version_date"], comp["old_version_date"],
            comp["action_type"], comp["new_content"], comp["old_content"], comp["reason"],
            json.dumps(comp["table_rows"], ensure_ascii=False), comp["source"],
            comp["source_url"], fetched_at, s2_path
        ))

    # 3. 解析 Sample 3 (單條確認)
    s3_res = parse_single_article(
        s3_html,
        raw_path=s3_path,
        source_url="https://lis.ly.gov.tw/lglawc/lawsingle?001D18E6E7520000000000000000014000000004000000^01830109123000^00000000000"
    )
    print(f"\nParsed Single Article 3 for Art {s3_res['article_no']}: comparison_url={s3_res['comparison_url']}")

    conn.commit()
    conn.close()
    print("\nSuccessfully seeded pilot articles into database!")


if __name__ == "__main__":
    seed_pilot()

