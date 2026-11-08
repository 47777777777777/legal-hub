import json
import os
import glob
import sqlite3

BASE_DIR = r"C:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub"
chlaw_path = os.path.join(BASE_DIR, "data", "ChLaw.json")
with open(chlaw_path, "r", encoding="utf-8-sig") as f:
    chlaw = json.load(f)

gz_files = glob.glob(os.path.join(BASE_DIR, "data", "raw", "lis", "gz", "*.html.gz"))
db_path = os.path.join(BASE_DIR, "data", "legal_hub.db")
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("SELECT COUNT(DISTINCT act_id), COUNT(1) FROM article_reasons")
r_acts, r_count = cur.fetchone()

cur.execute("SELECT COUNT(DISTINCT act_id), COUNT(1) FROM article_versions")
v_acts, v_count = cur.fetchone()

cur.execute("PRAGMA table_info(acts)")
cols = [r[1] for r in cur.fetchall()]
print(f"acts table columns: {cols}")

id_col = "id" if "id" in cols else "act_id"
cur.execute(f"SELECT {id_col}, name, pcode FROM acts WHERE {id_col} IN (SELECT DISTINCT act_id FROM article_reasons)")
existing_acts = cur.fetchall()

print(f"Total Laws in ChLaw.json: {len(chlaw.get('Laws', []))}")
print(f"Total .html.gz files in data/raw/lis/gz/: {len(gz_files)}")
print(f"DB article_reasons: {r_count} rows across {r_acts} distinct acts")
print(f"DB article_versions: {v_count} rows across {v_acts} distinct acts")
print("Existing acts with reasons in DB:")
for act in existing_acts[:15]:
    print(f"  - {act[0]}: {act[1]} ({act[2]})")
