"""
scripts/import_lis_payload.py

Runs on remote server to UPSERT data from data/lis_sync_payload.json
into SQLite tables without whole database replacement.
"""

import os
import sys
import json
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "legal_hub.db")
PAYLOAD_PATH = os.path.join(BASE_DIR, "data", "lis_sync_payload.json")

def main():
    if not os.path.exists(PAYLOAD_PATH):
        print(f"Error: {PAYLOAD_PATH} does not exist.")
        sys.exit(1)

    with open(PAYLOAD_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. UPSERT article_reasons
    reasons = data.get("article_reasons", [])
    for r in reasons:
        cur.execute("""
            INSERT INTO article_reasons (
                act_id, article_no, version_date, action_type, reason,
                source, source_url, fetched_at, raw_path, date_label_raw, date_raw,
                article_no_at_the_time, source_mode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(act_id, article_no, version_date) DO UPDATE SET
                action_type = excluded.action_type,
                reason = excluded.reason,
                source = excluded.source,
                source_url = excluded.source_url,
                fetched_at = excluded.fetched_at,
                raw_path = excluded.raw_path,
                date_label_raw = excluded.date_label_raw,
                date_raw = excluded.date_raw,
                article_no_at_the_time = excluded.article_no_at_the_time,
                source_mode = excluded.source_mode
        """, (
            r.get("act_id"), r.get("article_no"), r.get("version_date"),
            r.get("action_type"), r.get("reason"), r.get("source"),
            r.get("source_url"), r.get("fetched_at"), r.get("raw_path"),
            r.get("date_label_raw"), r.get("date_raw"),
            r.get("article_no_at_the_time"), r.get("source_mode")
        ))

    # 2. UPSERT article_comparison
    comps = data.get("article_comparison", [])
    for c in comps:
        cur.execute("""
            INSERT INTO article_comparison (
                act_id, article_no, new_version_date, old_version_date,
                action_type, new_content, old_content, reason, table_data,
                source, source_url, fetched_at, raw_path, date_label_raw, date_raw,
                article_no_at_the_time, source_mode, col_headers_json, cells_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(act_id, article_no, new_version_date) DO UPDATE SET
                old_version_date = excluded.old_version_date,
                action_type = excluded.action_type,
                new_content = excluded.new_content,
                old_content = excluded.old_content,
                reason = excluded.reason,
                table_data = excluded.table_data,
                source = excluded.source,
                source_url = excluded.source_url,
                fetched_at = excluded.fetched_at,
                raw_path = excluded.raw_path,
                date_label_raw = excluded.date_label_raw,
                date_raw = excluded.date_raw,
                article_no_at_the_time = excluded.article_no_at_the_time,
                source_mode = excluded.source_mode,
                col_headers_json = excluded.col_headers_json,
                cells_json = excluded.cells_json
        """, (
            c.get("act_id"), c.get("article_no"), c.get("new_version_date"),
            c.get("old_version_date"), c.get("action_type"), c.get("new_content"),
            c.get("old_content"), c.get("reason"), c.get("table_data"),
            c.get("source"), c.get("source_url"), c.get("fetched_at"),
            c.get("raw_path"), c.get("date_label_raw"), c.get("date_raw"),
            c.get("article_no_at_the_time"), c.get("source_mode"),
            c.get("col_headers_json"), c.get("cells_json")
        ))

    # 3. UPSERT article_versions
    versions = data.get("article_versions", [])
    for v in versions:
        cur.execute("""
            INSERT INTO article_versions (
                act_id, article_no, version_date, action_type, content,
                source, source_url, fetched_at, raw_path, date_label_raw, date_raw,
                article_no_at_the_time, source_mode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(act_id, article_no, version_date) DO UPDATE SET
                action_type = excluded.action_type,
                content = excluded.content,
                source = excluded.source,
                source_url = excluded.source_url,
                fetched_at = excluded.fetched_at,
                raw_path = excluded.raw_path,
                date_label_raw = excluded.date_label_raw,
                date_raw = excluded.date_raw,
                article_no_at_the_time = excluded.article_no_at_the_time,
                source_mode = excluded.source_mode
        """, (
            v.get("act_id"), v.get("article_no"), v.get("version_date"),
            v.get("action_type"), v.get("content"), v.get("source"),
            v.get("source_url"), v.get("fetched_at"), v.get("raw_path"),
            v.get("date_label_raw"), v.get("date_raw"),
            v.get("article_no_at_the_time"), v.get("source_mode")
        ))

    # 4. UPSERT source_attempts
    attempts = data.get("source_attempts", [])
    if attempts:
        # group by (source, act_id) and clean up before inserting to prevent infinite buildup
        seen_acts = set((a.get("source"), a.get("act_id")) for a in attempts if a.get("act_id"))
        for s, a_id in seen_acts:
            cur.execute("DELETE FROM source_attempts WHERE source = ? AND act_id = ?", (s, a_id))
        for att in attempts:
            cur.execute("""
                INSERT INTO source_attempts (
                    source, act_id, article_no, status, error_reason, duration_ms, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                att.get("source"), att.get("act_id"), att.get("article_no"),
                att.get("status"), att.get("error_reason"), att.get("duration_ms"),
                att.get("created_at") or "datetime('now')"
            ))

    # 5. UPSERT update_runs
    runs = data.get("update_runs", [])
    for rn in runs:
        cur.execute("""
            INSERT INTO update_runs (
                run_id, source, started_at, finished_at, status, counts_json, error, dry_run, mode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                finished_at = excluded.finished_at,
                status = excluded.status,
                counts_json = excluded.counts_json,
                error = excluded.error,
                dry_run = excluded.dry_run,
                mode = excluded.mode
        """, (
            rn.get("run_id"), rn.get("source"), rn.get("started_at"),
            rn.get("finished_at"), rn.get("status"), rn.get("counts_json"),
            rn.get("error"), rn.get("dry_run"), rn.get("mode") or "manual"
        ))

    conn.commit()

    cnt_reasons = cur.execute("SELECT count(*) FROM article_reasons").fetchone()[0]
    cnt_versions = cur.execute("SELECT count(*) FROM article_versions").fetchone()[0]
    cnt_attempts = cur.execute("SELECT count(*) FROM source_attempts WHERE source = 'lis'").fetchone()[0]
    cnt_comps = cur.execute("SELECT count(*) FROM article_comparison").fetchone()[0]
    cnt_runs = cur.execute("SELECT count(*) FROM update_runs WHERE source = 'lis'").fetchone()[0]
    conn.close()

    print("Remote UPSERT Complete:")
    print(f"  article_reasons count on remote:    {cnt_reasons}")
    print(f"  article_versions count on remote:   {cnt_versions}")
    print(f"  source_attempts count on remote:    {cnt_attempts}")
    print(f"  article_comparison count on remote: {cnt_comps}")
    print(f"  update_runs (lis) on remote:        {cnt_runs}")

if __name__ == "__main__":
    main()
