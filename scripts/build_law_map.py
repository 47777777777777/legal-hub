import sqlite3
import urllib.request
import re
import csv
import json
import datetime
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "legal_hub.db")
CHLAW_PATH = os.path.join(BASE_DIR, "data", "ChLaw.json")
REPORT_PATH = os.path.join(BASE_DIR, "reports", "law_map_unmatched.csv")

os.makedirs(os.path.join(BASE_DIR, "reports"), exist_ok=True)

# 12 Target Tier 1 Laws:
TIER1_TARGETS = [
    {
        "pcode": "A0000001",
        "act_id": "constitution",
        "name": "中華民國憲法",
        "lp_name": "中華民國憲法",
        "lp_act_url": "https://lawplayer.com/act/6437d027e800e5f0b9300e5d",
        "matched_by": "sitemap_verified"
    },
    {
        "pcode": "B0000001",
        "act_id": "civil_code",
        "name": "民法",
        "lp_name": "民法",
        "lp_act_url": "https://lawplayer.com/act/6437d054e800e5f0b930159a",
        "matched_by": "sitemap_verified"
    },
    {
        "pcode": "C0000001",
        "act_id": "criminal_code",
        "name": "中華民國刑法",
        "lp_name": "刑法",
        "lp_act_url": "https://lawplayer.com/act/6437d05ae800e5f0b9301656",
        "matched_by": "sitemap_verified"
    },
    {
        "pcode": "B0010001",
        "act_id": "civil_procedure_code",
        "name": "民事訴訟法",
        "lp_name": "民事訴訟法",
        "lp_act_url": "https://lawplayer.com/act/6437d054e800e5f0b93015aa",
        "matched_by": "sitemap_verified"
    },
    {
        "pcode": "C0010001",
        "act_id": "criminal_procedure_code",
        "name": "刑事訴訟法",
        "lp_name": "刑事訴訟法",
        "lp_act_url": "https://lawplayer.com/act/6437d05be800e5f0b9301674",
        "matched_by": "sitemap_verified"
    },
    {
        "pcode": "A0030055",
        "act_id": "admin_procedure_act",
        "name": "行政程序法",
        "lp_name": "行政程序法",
        "lp_act_url": "https://lawplayer.com/act/6437d040e800e5f0b9301329",
        "matched_by": "sitemap_verified"
    },
    {
        "pcode": "A0030154",
        "act_id": "admin_litigation_act",
        "name": "行政訴訟法",
        "lp_name": "行政訴訟法",
        "lp_act_url": "https://lawplayer.com/act/6437d046e800e5f0b93013f3",
        "matched_by": "sitemap_verified"
    },
    {
        "pcode": "J0080001",
        "act_id": "company_act",
        "name": "公司法",
        "lp_name": "公司法",
        "lp_act_url": "https://lawplayer.com/act/6437d1bfe800e5f0b9304389",
        "matched_by": "sitemap_verified"
    },
    {
        "pcode": "N0030001",
        "act_id": "labor_standards_act",
        "name": "勞動基準法",
        "lp_name": "勞動基準法",
        "lp_act_url": "https://lawplayer.com/act/6437d280e800e5f0b9305c1a",
        "matched_by": "sitemap_verified"
    },
    {
        "pcode": "J0070017",
        "act_id": "copyright_act",
        "name": "著作權法",
        "lp_name": "著作權法",
        "lp_act_url": "https://lawplayer.com/act/6437d1bde800e5f0b930433e",
        "matched_by": "sitemap_verified"
    },
    {
        "pcode": "I0050021",
        "act_id": "personal_data_protection_act",
        "name": "個人資料保護法",
        "lp_name": "個資法",
        "lp_act_url": "https://lawplayer.com/act/6437d19de800e5f0b9303f41",
        "matched_by": "sitemap_verified"
    },
    {
        "pcode": "K0040012",
        "act_id": "traffic_act",
        "name": "道路交通管理處罰條例",
        "lp_name": "道路交通管理處罰條例",
        "lp_act_url": "https://lawplayer.com/act/6437d202e800e5f0b9304be8",
        "matched_by": "sitemap_verified"
    }
]

def build_law_map():
    print("=== Building law_map Table & Unmatched Report ===")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # 1. Create table law_map idempotent
    cur.execute("""
        CREATE TABLE IF NOT EXISTS law_map (
            pcode TEXT PRIMARY KEY,
            act_id TEXT NOT NULL,
            lp_act_url TEXT NOT NULL,
            lp_name TEXT NOT NULL,
            matched_by TEXT NOT NULL,
            checked_at TEXT NOT NULL
        )
    """)
    
    # 2. Populate Tier 1 items
    now_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    matched_pcodes = set()
    
    for item in TIER1_TARGETS:
        cur.execute("""
            INSERT INTO law_map (pcode, act_id, lp_act_url, lp_name, matched_by, checked_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(pcode) DO UPDATE SET
                act_id = excluded.act_id,
                lp_act_url = excluded.lp_act_url,
                lp_name = excluded.lp_name,
                matched_by = excluded.matched_by,
                checked_at = excluded.checked_at
        """, (item["pcode"], item["act_id"], item["lp_act_url"], item["lp_name"], item["matched_by"], now_ts))
        matched_pcodes.add(item["pcode"])
        
    conn.commit()
    print(f"Populated {len(TIER1_TARGETS)} verified Tier 1 laws into law_map table.")
    
    # 3. Generate law_map_unmatched.csv for all other laws in MOJ ChLaw.json
    with open(CHLAW_PATH, "r", encoding="utf-8-sig") as f:
        chlaw = json.load(f)
        
    moj_laws = chlaw.get("Laws", [])
    unmatched_rows = []
    
    for law in moj_laws:
        name = law.get("LawName", "")
        url = law.get("LawURL", "")
        pcode = url.split("=")[-1] if "=" in url else ""
        if pcode in matched_pcodes:
            continue
        category = law.get("LawCategory", "")
        level = law.get("LawLevel", "")
        unmatched_rows.append({
            "pcode": pcode,
            "moj_name": name,
            "category": category,
            "level": level,
            "status": "UNMATCHED_NOT_TIER1",
            "reason": "Not in Tier 1 batch scope; pending Tier 2/3 alignment"
        })
        
    with open(REPORT_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["pcode", "moj_name", "category", "level", "status", "reason"])
        writer.writeheader()
        writer.writerows(unmatched_rows)
        
    print(f"Generated {REPORT_PATH} with {len(unmatched_rows)} unmatched laws.")
    
    # Verify count in law_map
    cur.execute("SELECT count(*) FROM law_map")
    total_in_map = cur.fetchone()[0]
    print(f"law_map total records: {total_in_map}")
    conn.close()
    
    return len(unmatched_rows), unmatched_rows[:20]

if __name__ == "__main__":
    count, top20 = build_law_map()
    print(f"\n--- Top 20 Unmatched Laws (Total: {count}) ---")
    for r in top20:
        print(f"[{r['pcode']}] {r['moj_name']} ({r['category']}) - {r['reason']}")
