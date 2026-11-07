import os
import sys
import shutil
import sqlite3
import hashlib
import json
import urllib.request
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# 1. MOJ network request details
print("=== 1-3.1 MOJ NETWORK REQUEST VERIFICATION ===")
moj_url = "https://law.moj.gov.tw/api/ch/law/json"
print(f"Requesting URL: {moj_url}")
start_t = datetime.now()
try:
    req = urllib.request.Request(
        moj_url,
        headers={"User-Agent": "LegalHub-Verification/1.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        content = resp.read()
        print(f"HTTP Status: {resp.status}")
        print(f"ETag: {resp.headers.get('ETag')}")
        print(f"Last-Modified: {resp.headers.get('Last-Modified')}")
        print(f"Downloaded Zip Size: {len(content)} bytes")
        print(f"Request Timestamp: {start_t.isoformat()}")
        
        # Check if zip
        if content.startswith(b"PK\x03\x04"):
            import zipfile
            import io
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                unzipped = z.read("ChLaw.json")
                downloaded_sha256 = hashlib.sha256(unzipped).hexdigest()
                print(f"Extracted ChLaw.json size: {len(unzipped)} bytes")
                print(f"Extracted ChLaw.json sha256: {downloaded_sha256}")
except Exception as e:
    print(f"Network request exception: {e}")

# Check local ChLaw.json sha256
chlaw_path = "data/ChLaw.json"
if os.path.exists(chlaw_path):
    with open(chlaw_path, "rb") as f:
        data = f.read()
        chlaw_sha = hashlib.sha256(data).hexdigest()
        mtime = datetime.fromtimestamp(os.path.getmtime(chlaw_path))
        print(f"Local ChLaw.json size: {len(data)} bytes")
        print(f"Local ChLaw.json sha256: {chlaw_sha}")
        print(f"Local ChLaw.json mtime: {mtime.isoformat()}")

print("\n=== 1-3.2 POSITIVE CONTROL DRY-RUN TEST ===")
# Create a copy of the database
db_orig = "data/legal_hub.db"
db_copy = "data/legal_hub_test_copy.db"
shutil.copy2(db_orig, db_copy)

try:
    conn = sqlite3.connect(db_copy)
    cur = conn.cursor()
    
    # Positive control mutations:
    # (a) Modify 1 article content
    cur.execute("SELECT act_id, article_no, content FROM articles WHERE act_id='admin_procedure_act' AND article_no='1'")
    orig_art = cur.fetchone()
    print(f"Original Art: act_id={orig_art[0]}, article_no={orig_art[1]}, content[:30]={orig_art[2][:30]}")
    mutated_content = orig_art[2] + "【正向對照測試修改字串】"
    cur.execute("UPDATE articles SET content=? WHERE act_id='admin_procedure_act' AND article_no='1'", 
                (mutated_content,))
    
    # (b) Modify 1 act name (same pcode, different name)
    cur.execute("SELECT id, name, pcode FROM acts WHERE id='constitution'")
    orig_act = cur.fetchone()
    print(f"Original Act: id={orig_act[0]}, name={orig_act[1]}, pcode={orig_act[2]}")
    mutated_act_name = orig_act[1] + "（正向對照測試改名）"
    cur.execute("UPDATE acts SET name=? WHERE id='constitution'", (mutated_act_name,))
    
    # (c) Delete 1 act row from DB (so source has it, DB does not -> add_act)
    cur.execute("SELECT id, name, pcode FROM acts WHERE id='personal_data_protection_act'")
    orig_del = cur.fetchone()
    print(f"Deleted Act from DB: id={orig_del[0]}, name={orig_del[1]}, pcode={orig_del[2]}")
    cur.execute("DELETE FROM articles WHERE act_id='personal_data_protection_act'")
    cur.execute("DELETE FROM acts WHERE id='personal_data_protection_act'")
    
    conn.commit()
    conn.close()
    
    # Now run moj dry-run pointing to db_copy
    from backend.updater.moj import MojSource
    from backend.updater.runner import execute_update_run
    
    test_conn = sqlite3.connect(db_copy)
    src = MojSource({"test_chlaw_file": "data/ChLaw.json"})
    
    print("\n--- Running execute_update_run(MojSource, apply=False) on mutated database ---")
    res = execute_update_run(src, apply=False, mode="test", conn=test_conn)
    print(f"Run status: {res.get('status')}")
    print(f"Run counts: {res.get('counts')}")
    changes = res.get("changes", [])
    print(f"Total changes count: {len(changes)}")
    for ch in changes:
        print(f"Change: type={ch.get('change_type')}, act_id={ch.get('act_id')}, article_no={ch.get('article_no')}, detail={ch.get('detail')}")
    test_conn.close()

finally:
    if os.path.exists(db_copy):
        try:
            os.remove(db_copy)
        except Exception:
            pass

print("\n=== 1-3.3 CATEGORY VS LAWABANDONNOTE DISCREPANCY ANALYSIS ===")
with open("data/ChLaw.json", "r", encoding="utf-8-sig") as f:
    chlaw_data = json.load(f)

laws = chlaw_data.get("Laws", [])
print(f"Total laws in ChLaw.json: {len(laws)}")

discrepancies = []
cat_abolished_count = 0
note_abolished_count = 0
both_count = 0

for law in laws:
    pcode = law.get("LawPcode")
    name = law.get("LawName")
    cat = law.get("LawCategory", "")
    note = law.get("LawAbandonNote", "")
    
    is_cat_abolished = "廢止法規" in cat
    is_note_abolished = bool(note and note.strip())
    
    if is_cat_abolished:
        cat_abolished_count += 1
    if is_note_abolished:
        note_abolished_count += 1
    if is_cat_abolished and is_note_abolished:
        both_count += 1
        
    if is_cat_abolished != is_note_abolished:
        discrepancies.append({
            "pcode": pcode,
            "name": name,
            "category": cat,
            "abandon_note": note,
            "is_cat_abolished": is_cat_abolished,
            "is_note_abolished": is_note_abolished
        })

print(f"Category contains '廢止法規': {cat_abolished_count}")
print(f"LawAbandonNote is non-empty: {note_abolished_count}")
print(f"Both agree: {both_count}")
print(f"Discrepancies count: {len(discrepancies)}")
if discrepancies:
    print("Discrepant acts:")
    for d in discrepancies[:10]:
        print(f"  Pcode: {d['pcode']}, Name: {d['name']}, Note: '{d['abandon_note']}', Cat: '{d['category']}'")
