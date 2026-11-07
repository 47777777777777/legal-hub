import sqlite3
import json
import re
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "legal_hub.db")
CHLAW_PATH = os.path.join(BASE_DIR, "data", "ChLaw.json")
CHORDER_PATH = os.path.join(BASE_DIR, "data", "ChOrder.json")

def clean_no(s: str) -> str:
    s = s.replace("第", "").replace("條", "").replace("之", "-").replace(" ", "").strip()
    return s

def populate_label_raw():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Load act mappings
    cur.execute("SELECT id, pcode FROM acts")
    acts = cur.fetchall()
    pcode_to_id = {}
    for aid, pcode in acts:
        if pcode:
            pcode_to_id[pcode.upper().strip()] = aid
        pcode_to_id[aid.lower().strip()] = aid

    # Read sources
    with open(CHLAW_PATH, "r", encoding="utf-8-sig") as f:
        laws = json.load(f)["Laws"]
    with open(CHORDER_PATH, "r", encoding="utf-8-sig") as f:
        orders = json.load(f)["Laws"]

    all_sources = laws + orders
    print(f"Loaded {len(all_sources)} acts from ChLaw.json and ChOrder.json.")

    updates = []
    total_articles_scanned = 0
    standard_labels = 0
    non_standard_labels = 0

    for act in all_sources:
        url = act.get("LawURL", "")
        m = re.search(r'[pP][cC]ode=([a-zA-Z0-9]+)', url)
        if not m:
            continue
        pcode = m.group(1).upper().strip()
        act_id = pcode_to_id.get(pcode) or pcode_to_id.get(pcode.lower())
        if not act_id:
            continue

        for item in act.get("LawArticles", []):
            if item.get("ArticleType") == "A":
                raw_no = item.get("ArticleNo", "").strip()
                art_no = clean_no(raw_no)
                total_articles_scanned += 1

                # Rule: Only if raw_no starts with 第 and ends with 條
                if raw_no.startswith("第") and raw_no.endswith("條"):
                    label_raw = raw_no
                    standard_labels += 1
                else:
                    label_raw = ""
                    non_standard_labels += 1

                updates.append((label_raw, act_id, art_no))

    print(f"Prepared {len(updates)} label_raw updates (Standard: {standard_labels}, Non-standard: {non_standard_labels}).")

    cur.executemany("UPDATE articles SET label_raw = ? WHERE act_id = ? AND article_no = ?", updates)
    conn.commit()

    # Verify counts in DB
    cur.execute("SELECT count(*) FROM articles WHERE label_raw IS NOT NULL AND label_raw <> ''")
    cnt_with_label = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM articles WHERE label_raw IS NULL OR label_raw = ''")
    cnt_without_label = cur.fetchone()[0]

    print(f"DB verification: Articles with label_raw: {cnt_with_label:,}, Articles without label_raw (empty): {cnt_without_label:,}")

    # Inspect samples
    cur.execute("SELECT act_id, article_no, label_raw FROM articles WHERE act_id IN ('criminal_code', 'civil_code', 'a0000005', 'a0000003') LIMIT 8")
    print("Samples:", cur.fetchall())

    conn.close()

if __name__ == "__main__":
    populate_label_raw()
