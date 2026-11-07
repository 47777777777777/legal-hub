import json
import sqlite3
import hashlib
import re
from pathlib import Path

import sys
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))
DB_PATH = BASE_DIR / "data" / "legal_hub.db"
CHLAW_PATH = BASE_DIR / "data" / "ChLaw.json"
CHORDER_PATH = BASE_DIR / "data" / "ChOrder.json"

from backend.db import init_database
init_database(str(DB_PATH))

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Get pcode to act_id mapping from acts table
cur.execute("SELECT id, pcode FROM acts")
pcode_to_act = {r["pcode"].upper(): r["id"] for r in cur.fetchall()}

seeded = []

def process_file(file_path):
    with open(file_path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
    for l in data["Laws"]:
        foreword = l.get("LawForeword", "").strip()
        if not foreword:
            continue
        law_url = l.get("LawURL", "")
        m = re.search(r'[pP][cC]ode=([a-zA-Z0-9]+)', law_url)
        if not m:
            continue
        pcode = m.group(1).upper()
        act_id = pcode_to_act.get(pcode, pcode.lower())
        h = hashlib.sha256(foreword.encode("utf-8")).hexdigest()
        
        cur.execute("""
            INSERT OR REPLACE INTO act_forewords (act_id, pcode, content, content_hash)
            VALUES (?, ?, ?, ?)
        """, (act_id, pcode, foreword, h))
        
        cur.execute("""
            UPDATE acts SET foreword = ? WHERE id = ? OR pcode = ?
        """, (foreword, act_id, pcode))
        
        seeded.append((act_id, pcode, l.get("LawName"), len(foreword)))

process_file(CHLAW_PATH)
process_file(CHORDER_PATH)

conn.commit()

# Verify
cur.execute("SELECT act_id, pcode, length(content) FROM act_forewords")
rows = cur.fetchall()
print(f"Total forewords in act_forewords: {len(rows)}")
for r in rows:
    print(f"  act_id={r['act_id']} pcode={r['pcode']} length={r[2]}")

conn.close()
