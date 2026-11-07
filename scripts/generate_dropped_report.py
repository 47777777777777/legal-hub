import json
import sqlite3
import csv
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CHLAW_PATH = BASE_DIR / "data" / "ChLaw.json"
CHORDER_PATH = BASE_DIR / "data" / "ChOrder.json"
DB_PATH = BASE_DIR / "data" / "legal_hub.db"
OUTPUT_CSV = BASE_DIR / "reports" / "dropped_source_content.csv"

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Preload acts and articles
cur.execute("SELECT id, pcode, chapters_json FROM acts")
act_rows = cur.fetchall()
pcode_to_act = {}
for r in act_rows:
    pcode_to_act[r["pcode"].upper()] = {
        "id": r["id"],
        "chapters": json.loads(r["chapters_json"]) if r["chapters_json"] else []
    }

cur.execute("SELECT act_id, article_no, content FROM articles")
articles_rows = cur.fetchall()
act_articles = {}
for r in articles_rows:
    if r["act_id"] not in act_articles:
        act_articles[r["act_id"]] = set()
    act_articles[r["act_id"]].add(r["article_no"])

# Check if act_forewords table exists
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='act_forewords'")
has_forewords_table = cur.fetchone() is not None
stored_forewords = set()
if has_forewords_table:
    cur.execute("SELECT pcode FROM act_forewords")
    for r in cur.fetchall():
        stored_forewords.add(r[0].upper())

conn.close()

dropped = []

def process_file(file_path):
    with open(file_path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
    
    for l in data["Laws"]:
        law_url = l.get("LawURL", "")
        m = re.search(r'[pP][cC]ode=([a-zA-Z0-9]+)', law_url)
        if not m:
            continue
        pcode = m.group(1).upper()
        act_info = pcode_to_act.get(pcode)
        act_id = act_info["id"] if act_info else pcode
        
        # 1. Check foreword
        foreword = l.get("LawForeword", "").strip()
        if foreword:
            if pcode not in stored_forewords:
                dropped.append({
                    "act": f"{pcode} ({l.get('LawName')})",
                    "object_index": "0 (Foreword)",
                    "article_type": "Foreword",
                    "preview": foreword[:40].replace("\r", " ").replace("\n", " ")
                })
        
        # 2. Check articles and chapters
        raw_items = l.get("LawArticles", [])
        stored_arts = act_articles.get(act_id, set()) if act_info else set()
        stored_chaps = act_info["chapters"] if act_info else []
        chap_titles = {c.get("title", "").strip() for c in stored_chaps}
        
        for idx, item in enumerate(raw_items, 1):
            itype = item.get("ArticleType", "")
            icontent = item.get("ArticleContent", "").strip()
            ino = item.get("ArticleNo", "").replace("第", "").replace("條", "").strip()
            
            if itype == "A":
                if ino not in stored_arts:
                    dropped.append({
                        "act": f"{pcode} ({l.get('LawName')})",
                        "object_index": str(idx),
                        "article_type": "A",
                        "preview": icontent[:40].replace("\r", " ").replace("\n", " ")
                    })
            elif itype == "C":
                # Check if chapter is stored in chapters_json
                norm_title = " ".join([p.strip() for p in icontent.replace("\r", " ").replace("\n", " ").split() if p.strip()])
                if not any(norm_title in c or c in norm_title for c in chap_titles):
                    dropped.append({
                        "act": f"{pcode} ({l.get('LawName')})",
                        "object_index": str(idx),
                        "article_type": "C",
                        "preview": icontent[:40].replace("\r", " ").replace("\n", " ")
                    })

process_file(CHLAW_PATH)
process_file(CHORDER_PATH)

OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["act", "object_index", "article_type", "preview"])
    writer.writeheader()
    for row in dropped:
        writer.writerow(row)

print(f"Total dropped items found: {len(dropped)}")
for d in dropped:
    print(f"  {d['act']} | Item {d['object_index']} ({d['article_type']}): {d['preview']}")

