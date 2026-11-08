import os
import sys
import glob
import gzip
import sqlite3

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from backend.lis.parser import parse_full_act_reasons
from backend.db import DB_FILE

RAW_GZ_DIR = os.path.join(BASE_DIR, "data", "raw", "lis", "gz")

def reingest():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Get map of pcode -> act_id
    cur.execute("SELECT id, pcode, name FROM acts")
    pcode_map = {}
    for r in cur.fetchall():
        if r[1]:
            pcode_map[r[1].upper()] = (r[0], r[2])

    gz_files = glob.glob(os.path.join(RAW_GZ_DIR, "*.html.gz"))
    print(f"Found {len(gz_files)} .html.gz files to re-parse and re-ingest.")

    total_reasons = 0
    total_versions = 0

    for gz_path in gz_files:
        filename = os.path.basename(gz_path)
        pcode = filename.replace(".html.gz", "").upper()
        if pcode not in pcode_map:
            print(f"Skipping {filename}: pcode {pcode} not in DB acts.")
            continue

        act_id, name = pcode_map[pcode]

        with gzip.open(gz_path, "rt", encoding="utf-8", errors="ignore") as f:
            html = f.read()

        raw_relpath = os.path.relpath(gz_path, BASE_DIR).replace("\\", "/")
        parsed = parse_full_act_reasons(html, raw_path=raw_relpath)

        cur.execute("BEGIN TRANSACTION;")
        cur.execute("DELETE FROM article_reasons WHERE act_id = ? AND source = '立法院法律系統'", (act_id,))
        cur.execute("DELETE FROM article_versions WHERE act_id = ? AND source = '立法院法律系統'", (act_id,))

        r_cnt = 0
        v_cnt = 0
        for r in parsed:
            art_no = r["article_no"]
            v_date = r["version_date"]
            action_type = r.get("action_type", "")
            reason_text = r.get("reason", "")
            content_text = r.get("content", "")
            date_label = r.get("date_label_raw", f"({v_date} {action_type})")
            art_at_time = r.get("article_no_at_the_time", art_no)

            if reason_text:
                cur.execute("""
                    INSERT INTO article_reasons (
                        act_id, article_no, version_date, action_type, reason,
                        date_label_raw, date_raw, article_no_at_the_time, source_mode,
                        source, source_url, raw_path, fetched_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """, (
                    act_id, art_no, v_date, action_type, reason_text,
                    date_label, v_date, art_at_time, "fullpage",
                    "立法院法律系統", r.get("source_url", ""), raw_relpath
                ))
                r_cnt += 1

            if content_text:
                cur.execute("""
                    INSERT INTO article_versions (
                        act_id, article_no, version_date, action_type, content,
                        date_label_raw, date_raw, article_no_at_the_time, source_mode,
                        source, source_url, raw_path, fetched_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """, (
                    act_id, art_no, v_date, action_type, content_text,
                    date_label, v_date, art_at_time, "fullpage",
                    "立法院法律系統", r.get("source_url", ""), raw_relpath
                ))
                v_cnt += 1

        cur.execute("DELETE FROM source_attempts WHERE source = 'lis' AND act_id = ?", (act_id,))
        cur.execute("""
            INSERT INTO source_attempts (source, act_id, article_no, status, duration_ms, created_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        """, ("lis", act_id, "*", "found" if r_cnt > 0 else "no_data", 0))

        conn.commit()
        total_reasons += r_cnt
        total_versions += v_cnt

    conn.close()
    print(f"Reingestion complete! Total reasons: {total_reasons}, Total versions: {total_versions}")

if __name__ == "__main__":
    reingest()

