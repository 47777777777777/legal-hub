import os
import sys
import sqlite3
import csv
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(BASE_DIR, "data", "legal_hub.db")
output_csv = os.path.join(BASE_DIR, "reports", "coverage_matrix.csv")

print("=== 2-3 GENERATING COVERAGE MATRIX ===")
start_t = datetime.now()

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Preload data for batch performance across 11,804 acts & 222,116 articles
print("Preloading database indexes...")

# 1. Acts info: id -> {name, pcode, status, category, has_history}
cur.execute("SELECT id, name, pcode, status, category, (history_json IS NOT NULL AND history_json != '[]' AND history_json != '') FROM acts")
acts_dict = {}
for r in cur.fetchall():
    acts_dict[r[0]] = {
        "name": r[1],
        "pcode": r[2] or "",
        "status": r[3] or "active",
        "category": r[4] or "",
        "has_history": bool(r[5])
    }

# 2. Article counts per act: act_id -> count
cur.execute("SELECT act_id, count(*) FROM articles GROUP BY act_id")
act_art_counts = {r[0]: r[1] for r in cur.fetchall()}

# 3. LIS data per act & article:
cur.execute("SELECT DISTINCT act_id FROM law_legislative_history")
acts_with_lis_hist = {r[0] for r in cur.fetchall()}

cur.execute("SELECT DISTINCT act_id, article_no FROM article_reasons")
arts_with_reasons = {(r[0], r[1]) for r in cur.fetchall()}

cur.execute("SELECT DISTINCT act_id, article_no FROM article_comparison")
arts_with_comp = {(r[0], r[1]) for r in cur.fetchall()}

# Group LIS articles by act
act_lis_arts = {}
for aid, ano in arts_with_reasons.union(arts_with_comp):
    act_lis_arts.setdefault(aid, set()).add(ano)

# 4. LawPlayer enrichments per act & article
cur.execute("SELECT DISTINCT act_id, article_no FROM article_enrichments WHERE summary != '' OR vernacular_qa_json != '[]' OR practical_insights_json != '[]'")
arts_with_enr = {(r[0], r[1]) for r in cur.fetchall()}

cur.execute("SELECT pcode, act_id, (checked_at IS NOT NULL AND checked_at != ''), (not_found_at IS NOT NULL AND not_found_at != '') FROM law_map")
law_map_checked_pcodes = set()
law_map_checked_acts = set()
for r in cur.fetchall():
    if r[2] or r[3]:
        if r[0]: law_map_checked_pcodes.add(r[0].upper())
        if r[1]: law_map_checked_acts.add(r[1])

# Group enr articles by act
act_enr_arts = {}
for aid, ano in arts_with_enr:
    act_enr_arts.setdefault(aid, set()).add(ano)

# 5. Literature articles
cur.execute("SELECT act_id, article_no FROM literature_articles")
arts_with_lit = {(r[0], r[1]) for r in cur.fetchall()}
act_lit_arts = {}
for aid, ano in arts_with_lit:
    act_lit_arts.setdefault(aid, set()).add(ano)

# Summary counters for: 法律 (現行), 命令 (現行), 廢止
summary = {
    "法律": {"acts": 0, "arts": 0, "lis_present": 0, "lis_none": 0, "lis_not_att": 0, "lis_na": 0, "lp_present": 0, "lp_none": 0, "lp_not_att": 0, "hist_present": 0},
    "命令": {"acts": 0, "arts": 0, "lis_present": 0, "lis_none": 0, "lis_not_att": 0, "lis_na": 0, "lp_present": 0, "lp_none": 0, "lp_not_att": 0, "hist_present": 0},
    "廢止": {"acts": 0, "arts": 0, "lis_present": 0, "lis_none": 0, "lis_not_att": 0, "lis_na": 0, "lp_present": 0, "lp_none": 0, "lp_not_att": 0, "hist_present": 0}
}

os.makedirs(os.path.dirname(output_csv), exist_ok=True)
csv_rows = []

headers = [
    "act_id", "act_name", "pcode", "act_type", "status", "category", "total_articles",
    "official_text_present", "official_text_source_has_none",
    "act_history_present", "act_history_source_has_none",
    "lis_present", "lis_source_has_none", "lis_not_attempted", "lis_not_applicable",
    "lp_present", "lp_source_has_none", "lp_not_attempted",
    "jud_not_attempted",
    "lit_present", "lit_source_has_none"
]

for act_id, info in acts_dict.items():
    name = info["name"]
    pcode = info["pcode"]
    act_status = info["status"]
    cat = info["category"]
    art_count = act_art_counts.get(act_id, 0)
    
    # Classify into 法律 / 命令 / 廢止
    is_abolished = (act_status == "abolished") or ("廢止法規" in cat)
    if is_abolished:
        act_type = "廢止"
    elif "命令" in cat:
        act_type = "命令"
    else:
        act_type = "法律"
        
    s = summary[act_type]
    s["acts"] += 1
    s["arts"] += art_count
    
    # 1. official_text
    off_pres = art_count
    off_none = 0
    
    # 2. act_history
    if info["has_history"]:
        hist_pres = art_count
        hist_none = 0
        s["hist_present"] += art_count
    else:
        hist_pres = 0
        hist_none = art_count
        
    # 3. LIS
    is_order = ("命令" in cat) or ("行政規則" in cat)
    if is_order:
        lis_pres = 0
        lis_none = 0
        lis_not_att = 0
        lis_na = art_count
        s["lis_na"] += art_count
    else:
        # Check primary statute
        pres_count = len(act_lis_arts.get(act_id, set()))
        lis_pres = pres_count
        has_lis_attempt = (act_id in acts_with_lis_hist) or (pres_count > 0)
        if has_lis_attempt:
            lis_none = max(0, art_count - pres_count)
            lis_not_att = 0
            lis_na = 0
            s["lis_present"] += pres_count
            s["lis_none"] += lis_none
        else:
            lis_none = 0
            lis_not_att = art_count
            lis_na = 0
            s["lis_not_att"] += art_count
            
    # 4. LawPlayer
    lp_pres = len(act_enr_arts.get(act_id, set()))
    s["lp_present"] += lp_pres
    has_lp_attempt = (act_id in law_map_checked_acts) or (pcode.upper() in law_map_checked_pcodes) or (lp_pres > 0)
    if has_lp_attempt:
        lp_none = max(0, art_count - lp_pres)
        lp_not_att = 0
        s["lp_none"] += lp_none
    else:
        lp_none = 0
        lp_not_att = max(0, art_count - lp_pres)
        s["lp_not_att"] += lp_not_att
        
    # 5. Judicial
    jud_not_att = art_count
    
    # 6. Literature
    lit_pres = len(act_lit_arts.get(act_id, set()))
    lit_none = max(0, art_count - lit_pres)
    
    csv_rows.append([
        act_id, name, pcode, act_type, act_status, cat, art_count,
        off_pres, off_none,
        hist_pres, hist_none,
        lis_pres, lis_none, lis_not_att, lis_na,
        lp_pres, lp_none, lp_not_att,
        jud_not_att,
        lit_pres, lit_none
    ])

with open(output_csv, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(headers)
    writer.writerows(csv_rows)

end_t = datetime.now()
print(f"Generated {len(csv_rows)} rows in {output_csv} in {(end_t - start_t).total_seconds():.1f}s.")

print("\n=== 全庫覆蓋矩陣彙總（法律 / 命令 / 廢止）===")
print(f"{'類別':<6} | {'部數':<6} | {'總條數':<8} | {'法規沿革 present':<16} | {'LIS present':<12} | {'LIS none':<10} | {'LIS not_att':<12} | {'LIS N/A':<10} | {'LP present':<10} | {'LP not_att':<10}")
print("-" * 120)
for k in ["法律", "命令", "廢止"]:
    sm = summary[k]
    print(f"{k:<6} | {sm['acts']:<6} | {sm['arts']:<8} | {sm['hist_present']:<16} | {sm['lis_present']:<12} | {sm['lis_none']:<10} | {sm['lis_not_att']:<12} | {sm['lis_na']:<10} | {sm['lp_present']:<10} | {sm['lp_not_att']:<10}")

conn.close()

