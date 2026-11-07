import os
import sys
import json
import sqlite3
import datetime

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.lis.parser import (
    parse_full_act_reasons,
    parse_comparison_table,
    parse_comparisons_from_html
)

DB_PATH = os.path.join(BASE_DIR, "data", "legal_hub.db")
SAMPLE_DIR = os.path.join(BASE_DIR, "data", "raw", "lis", "samples")
COMP_DIR = os.path.join(BASE_DIR, "data", "raw", "lis", "comparisons")

def import_act(act_id="admin_procedure_act"):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Check MOJ articles count
    moj_arts = cur.execute("SELECT article_no FROM articles WHERE act_id = ?", (act_id,)).fetchall()
    moj_count = len(moj_arts)
    print(f"MOJ registered articles for {act_id}: {moj_count}")

    # Read Sample 1
    s1_path = os.path.join(SAMPLE_DIR, "sample_1.html")
    with open(s1_path, "r", encoding="utf-8", errors="ignore") as f:
        s1_html = f.read()

    # Read Sample 2
    s2_path = os.path.join(SAMPLE_DIR, "sample_2.html")
    with open(s2_path, "r", encoding="utf-8", errors="ignore") as f:
        s2_html = f.read()

    fetched_at = "2026-11-03"
    s1_url = "https://lis.ly.gov.tw/lglawc/lawsingle?001D18E6E7520000000000000000032000000007000000^01830109123000^00000000000"
    s2_url = "https://lis.ly.gov.tw/lglawc/lawsingle?001D18E6E752000000000000000005A00000000C00FFFFFD00^01830109123000^00000000000"

    # 1. Parse Full Act
    all_arts = parse_full_act_reasons(
        s1_html,
        raw_path=s1_path,
        source_url=s1_url
    )
    print(f"Parsed {len(all_arts)} historical version records from {s1_path}")

    # Clean existing records for this act before full import
    cur.execute("DELETE FROM article_reasons WHERE act_id = ?", (act_id,))
    cur.execute("DELETE FROM article_versions WHERE act_id = ?", (act_id,))
    cur.execute("DELETE FROM article_comparison WHERE act_id = ?", (act_id,))

    reasons_inserted = 0
    versions_inserted = 0

    for a in all_arts:
        cur.execute("""
            INSERT INTO article_reasons (
                act_id, article_no, version_date, action_type, reason,
                source, source_url, fetched_at, raw_path,
                date_label_raw, date_raw, article_no_at_the_time, source_mode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            act_id, a["article_no"], a["version_date"], a["action_type"], a["reason"],
            a["source"], a["source_url"], fetched_at, s1_path,
            a["date_label_raw"], a["date_raw"], a["article_no_at_the_time"], a["source_mode"]
        ))
        reasons_inserted += 1

        cur.execute("""
            INSERT INTO article_versions (
                act_id, article_no, version_date, action_type, content,
                source, source_url, fetched_at, raw_path,
                date_label_raw, date_raw, article_no_at_the_time, source_mode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            act_id, a["article_no"], a["version_date"], a["action_type"], a["content"],
            a["source"], a["source_url"], fetched_at, s1_path,
            a["date_label_raw"], a["date_raw"], a["article_no_at_the_time"], a["source_mode"]
        ))
        versions_inserted += 1

    # 2. Parse All Available Comparison Tables
    comp_inserted = 0
    comp_files = []
    if os.path.exists(COMP_DIR):
        comp_files = [os.path.join(COMP_DIR, f) for f in sorted(os.listdir(COMP_DIR)) if f.startswith("comp_") and f.endswith(".html")]

    if not comp_files and os.path.exists(s2_path):
        comp_files = [s2_path]

    for c_path in comp_files:
        with open(c_path, "r", encoding="utf-8", errors="ignore") as f:
            c_html = f.read()
        c_url = f"https://lis.ly.gov.tw/lglawc/lawsingle?001D18E6E752000000000000000005A00000000C00FFFFFD00^{os.path.basename(c_path)}"
        comparisons = parse_comparisons_from_html(c_html, raw_path=c_path, source_url=c_url)
        for comp in comparisons:
            if comp and comp.get("article_no"):
                cur.execute("""
                    INSERT INTO article_comparison (
                        act_id, article_no, new_version_date, old_version_date, action_type,
                        new_content, old_content, reason, table_data,
                        source, source_url, fetched_at, raw_path,
                        date_label_raw, date_raw, article_no_at_the_time, source_mode,
                        col_headers_json, cells_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    act_id, comp["article_no"], comp["new_version_date"], comp["old_version_date"],
                    comp["action_type"], comp["new_content"], comp["old_content"], comp["reason"],
                    json.dumps(comp["table_rows"], ensure_ascii=False),
                    comp["source"], comp["source_url"], fetched_at, c_path,
                    comp["date_label_raw"], comp["date_raw"], comp["article_no_at_the_time"], comp["source_mode"],
                    comp["col_headers_json"], comp["cells_json"]
                ))
                comp_inserted += 1

    conn.commit()
    conn.close()

    print(f"\nImport Completed:")
    print(f"  article_reasons inserted: {reasons_inserted}")
    print(f"  article_versions inserted: {versions_inserted}")
    print(f"  article_comparison inserted: {comp_inserted}")

if __name__ == "__main__":
    import_act()

