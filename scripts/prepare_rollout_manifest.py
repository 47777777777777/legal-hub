import json
import os
import sqlite3

BASE_DIR = r"C:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub"
DB_PATH = os.path.join(BASE_DIR, "data", "legal_hub.db")
CHLAW_PATH = os.path.join(BASE_DIR, "data", "ChLaw.json")
RAW_GZ_DIR = os.path.join(BASE_DIR, "data", "raw", "lis", "gz")

with open(CHLAW_PATH, "r", encoding="utf-8-sig") as f:
    chlaw = json.load(f)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

manifest = []
already_done = []

for l in chlaw.get("Laws", []):
    law_name = l.get("LawName")
    law_url = l.get("LawURL", "")
    pcode = law_url.split("pcode=")[-1].strip() if "pcode=" in law_url else ""
    if not pcode:
        pcode = law_url.split("PCode=")[-1].strip() if "PCode=" in law_url else ""

    cur.execute("SELECT id, name, pcode FROM acts WHERE name = ?", (law_name,))
    row = cur.fetchone()
    if not row:
        cur.execute("SELECT id, name, pcode FROM acts WHERE pcode = ?", (pcode,))
        row = cur.fetchone()

    act_id = row["id"] if row else pcode.lower()
    
    # Check if already in source_attempts
    cur.execute("SELECT status FROM source_attempts WHERE source = 'lis' AND act_id = ?", (act_id,))
    attempt = cur.fetchone()

    gz_file = os.path.join(RAW_GZ_DIR, f"{pcode}.html.gz")
    has_gz = os.path.exists(gz_file)

    cur.execute("SELECT COUNT(1) FROM article_reasons WHERE act_id = ?", (act_id,))
    reasons_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(1) FROM article_versions WHERE act_id = ?", (act_id,))
    versions_count = cur.fetchone()[0]

    item = {
        "act_id": act_id,
        "name": law_name,
        "pcode": pcode,
        "has_gz": has_gz,
        "attempt_status": attempt["status"] if attempt else None,
        "reasons_count": reasons_count,
        "versions_count": versions_count,
    }

    if (attempt and attempt["status"] in ("found", "no_data")) and (has_gz or attempt["status"] == "no_data"):
        already_done.append(item)
    else:
        manifest.append(item)

conn.close()

print(f"Total laws in ChLaw.json: {len(chlaw.get('Laws', []))}")
print(f"Already completed laws:   {len(already_done)}")
print(f"Remaining laws to crawl:  {len(manifest)}")

# Split into batches of 100
batches = [manifest[i:i + 100] for i in range(0, len(manifest), 100)]
print(f"Total batches (100/batch): {len(batches)}")
for idx, b in enumerate(batches):
    print(f"  Batch {idx + 1}: {len(b)} laws (e.g. {b[0]['name']} ... {b[-1]['name']})")

