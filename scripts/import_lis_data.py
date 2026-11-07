import os
import sys
import json
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.db import init_database

DB_PATH = os.path.join(BASE_DIR, "data", "legal_hub.db")
IN_PATH = os.path.join(BASE_DIR, "data", "lis_export.json")

def import_lis():
    init_database()  # Run migrations
    
    if not os.path.exists(IN_PATH):
        print(f"Error: {IN_PATH} does not exist.")
        return
        
    with open(IN_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    reasons = data.get("article_reasons", [])
    versions = data.get("article_versions", [])
    comparisons = data.get("article_comparison", [])
    
    # 1. Upsert reasons
    r_upserted = 0
    for r in reasons:
        cur.execute("""
            SELECT id FROM article_reasons 
            WHERE act_id = ? AND article_no = ? AND version_date = ?
        """, (r["act_id"], r["article_no"], r["version_date"]))
        existing = cur.fetchone()
        if existing:
            cur.execute("""
                UPDATE article_reasons SET
                    action_type = ?, reason = ?, source = ?, source_url = ?, fetched_at = ?,
                    raw_path = ?, date_label_raw = ?, date_raw = ?, article_no_at_the_time = ?, source_mode = ?
                WHERE id = ?
            """, (
                r["action_type"], r["reason"], r["source"], r["source_url"], r["fetched_at"],
                r["raw_path"], r["date_label_raw"], r["date_raw"], r["article_no_at_the_time"], r["source_mode"],
                existing[0]
            ))
        else:
            cur.execute("""
                INSERT INTO article_reasons (
                    act_id, article_no, version_date, action_type, reason, source, source_url,
                    fetched_at, raw_path, date_label_raw, date_raw, article_no_at_the_time, source_mode
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                r["act_id"], r["article_no"], r["version_date"], r["action_type"], r["reason"],
                r["source"], r["source_url"], r["fetched_at"], r["raw_path"],
                r["date_label_raw"], r["date_raw"], r["article_no_at_the_time"], r["source_mode"]
            ))
        r_upserted += 1
        
    # 2. Upsert versions
    v_upserted = 0
    for v in versions:
        cur.execute("""
            SELECT id FROM article_versions 
            WHERE act_id = ? AND article_no = ? AND version_date = ?
        """, (v["act_id"], v["article_no"], v["version_date"]))
        existing = cur.fetchone()
        if existing:
            cur.execute("""
                UPDATE article_versions SET
                    action_type = ?, content = ?, source = ?, source_url = ?, fetched_at = ?,
                    raw_path = ?, date_label_raw = ?, date_raw = ?, article_no_at_the_time = ?, source_mode = ?
                WHERE id = ?
            """, (
                v["action_type"], v["content"], v["source"], v["source_url"], v["fetched_at"],
                v["raw_path"], v["date_label_raw"], v["date_raw"], v["article_no_at_the_time"], v["source_mode"],
                existing[0]
            ))
        else:
            cur.execute("""
                INSERT INTO article_versions (
                    act_id, article_no, version_date, action_type, content, source, source_url,
                    fetched_at, raw_path, date_label_raw, date_raw, article_no_at_the_time, source_mode
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                v["act_id"], v["article_no"], v["version_date"], v["action_type"], v["content"],
                v["source"], v["source_url"], v["fetched_at"], v["raw_path"],
                v["date_label_raw"], v["date_raw"], v["article_no_at_the_time"], v["source_mode"]
            ))
        v_upserted += 1
        
    # 3. Upsert comparisons
    c_upserted = 0
    for c in comparisons:
        cur.execute("""
            SELECT id FROM article_comparison 
            WHERE act_id = ? AND article_no = ? AND new_version_date = ?
        """, (c["act_id"], c["article_no"], c["new_version_date"]))
        existing = cur.fetchone()
        if existing:
            cur.execute("""
                UPDATE article_comparison SET
                    old_version_date = ?, action_type = ?, new_content = ?, old_content = ?,
                    reason = ?, table_data = ?, source = ?, source_url = ?, fetched_at = ?,
                    raw_path = ?, date_label_raw = ?, date_raw = ?, article_no_at_the_time = ?, source_mode = ?,
                    col_headers_json = ?, cells_json = ?
                WHERE id = ?
            """, (
                c["old_version_date"], c["action_type"], c["new_content"], c["old_content"],
                c["reason"], c.get("table_data", "[]"), c["source"], c["source_url"], c["fetched_at"],
                c["raw_path"], c["date_label_raw"], c["date_raw"], c["article_no_at_the_time"], c["source_mode"],
                c["col_headers_json"], c["cells_json"], existing[0]
            ))
        else:
            cur.execute("""
                INSERT INTO article_comparison (
                    act_id, article_no, new_version_date, old_version_date, action_type,
                    new_content, old_content, reason, table_data, source, source_url,
                    fetched_at, raw_path, date_label_raw, date_raw, article_no_at_the_time, source_mode,
                    col_headers_json, cells_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                c["act_id"], c["article_no"], c["new_version_date"], c["old_version_date"],
                c["action_type"], c["new_content"], c["old_content"], c["reason"],
                c.get("table_data", "[]"), c["source"], c["source_url"], c["fetched_at"],
                c["raw_path"], c["date_label_raw"], c["date_raw"], c["article_no_at_the_time"], c["source_mode"],
                c["col_headers_json"], c["cells_json"]
            ))
        c_upserted += 1
        
    conn.commit()
    conn.close()
    
    print(f"Import/UPSERT LIS Completed:")
    print(f"  article_reasons upserted: {r_upserted}")
    print(f"  article_versions upserted: {v_upserted}")
    print(f"  article_comparison upserted: {c_upserted}")

if __name__ == "__main__":
    import_lis()
