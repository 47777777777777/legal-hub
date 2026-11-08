"""
scripts/run_batch_rollout.py

Orchestrates batch crawling of the remaining 1,300+ statutes from Legislative Yuan (LIS).
Strictly adheres to Prompt 4I rules:
- 1 request / second throttling minimum.
- Generic browser User-Agent.
- Immediate critical stop on HTTP 403, 429, or captcha page.
- Stop-loss: single-batch parse failure rate > 5%, random sample mismatch, or Check 9 failure.
- Verbatim provenance: raw compressed files in data/raw/lis/gz/{pcode}.html.gz.
- Database atomic transactions per law into article_reasons, article_versions, source_attempts.
- Updates reports/lis_rollout_progress.md after each batch.
- Synchronizes batch payload to remote server via sync_lis_to_remote.py.
"""

import os
import sys
import time
import json
import random
import gzip
import sqlite3
import argparse
import subprocess

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from scripts.lis_crawler_pipeline import LisCrawler, RAW_GZ_DIR, NO_FULLPAGE_CSV
from backend.db import DB_FILE

CHLAW_PATH = os.path.join(BASE_DIR, "data", "ChLaw.json")
PROGRESS_MD = os.path.join(BASE_DIR, "reports", "lis_rollout_progress.md")
FAILED_LOG = os.path.join(BASE_DIR, "reports", "lis_failed_acts.csv")

def get_full_manifest():
    with open(CHLAW_PATH, "r", encoding="utf-8-sig") as f:
        chlaw = json.load(f)

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    manifest = []
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
        manifest.append({
            "act_id": act_id,
            "name": law_name,
            "pcode": pcode
        })
    conn.close()
    return manifest

def is_already_done(act_id, pcode):
    gz_file = os.path.join(RAW_GZ_DIR, f"{pcode}.html.gz")
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT status FROM source_attempts WHERE source = 'lis' AND act_id = ?", (act_id,))
    attempt = cur.fetchone()
    conn.close()
    if attempt and attempt[0] in ("found", "no_data"):
        return True
    return False

def verify_sample(act_id, pcode):
    gz_file = os.path.join(RAW_GZ_DIR, f"{pcode}.html.gz")
    if not os.path.exists(gz_file):
        return True
    
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT article_no, version_date, content FROM article_versions WHERE act_id = ?", (act_id,))
    v_rows = cur.fetchall()
    cur.execute("SELECT article_no, version_date, reason FROM article_reasons WHERE act_id = ?", (act_id,))
    r_rows = cur.fetchall()
    conn.close()

    if not v_rows and not r_rows:
        return True

    with gzip.open(gz_file, "rt", encoding="utf-8", errors="ignore") as f:
        raw_html = f.read()

    import re
    from bs4 import BeautifulSoup
    import html as html_lib
    raw_text = BeautifulSoup(raw_html, 'html.parser').get_text()
    clean_raw = re.sub(r'\s+', '', html_lib.unescape(raw_text))
    
    if v_rows:
        sample_v = random.choice(v_rows)
        if sample_v["content"]:
            clean_content = re.sub(r'\s+', '', html_lib.unescape(sample_v["content"]))
            if clean_content and clean_content not in clean_raw:
                print(f"[STOP-LOSS ERROR] Sample version article {sample_v['article_no']} ({sample_v['version_date']}) content mismatch in {act_id}!")
                return False

    if r_rows:
        sample_r = random.choice(r_rows)
        if sample_r["reason"]:
            clean_reason = re.sub(r'\s+', '', html_lib.unescape(sample_r["reason"]))
            if clean_reason and clean_reason not in clean_raw:
                print(f"[STOP-LOSS ERROR] Sample reason article {sample_r['article_no']} ({sample_r['version_date']}) reason mismatch in {act_id}!")
                return False

    return True

def run_batch(batch_num, acts, crawler):
    print(f"\n==========================================")
    print(f"=== STARTING BATCH {batch_num} ({len(acts)} acts) ===")
    print(f"==========================================")

    batch_start = time.time()
    succeeded = 0
    no_history = 0
    failed = 0
    total_reasons = 0
    total_versions = 0
    batch_reqs = 0

    for idx, item in enumerate(acts):
        name = item["name"]
        act_id = item["act_id"]
        pcode = item["pcode"]

        if is_already_done(act_id, pcode):
            print(f"[{idx+1}/{len(acts)}] Already done: {name} ({act_id}, {pcode})")
            succeeded += 1
            continue

        print(f"[{idx+1}/{len(acts)}] Crawling {name} ({act_id}, {pcode}) ...")
        try:
            res = crawler.crawl_act(name, act_id, pcode)
            batch_reqs += res.get("req_count", 0)

            if not res.get("success"):
                if res.get("error") == "no_fullpage":
                    print(f"  -> No history link on LIS. Recorded as no_data.")
                    # Ingest source_attempts as no_data
                    conn = sqlite3.connect(DB_FILE)
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO source_attempts (source, act_id, article_no, status, duration_ms, created_at)
                        VALUES (?, ?, ?, ?, ?, datetime('now'))
                    """, ("lis", act_id, "*", "no_data", int(res.get("duration", 0) * 1000)))
                    conn.commit()
                    conn.close()
                    no_history += 1
                else:
                    print(f"  -> FAILED: {res.get('error')}")
                    with open(FAILED_LOG, "a", encoding="utf-8") as f:
                        f.write(f"{act_id},{pcode},{name},{res.get('error')}\n")
                    failed += 1
                continue

            # Ingest into DB
            crawler.ingest_act(res)
            reasons_cnt = res.get("reasons_count", 0)
            total_reasons += reasons_cnt
            succeeded += 1
            print(f"  -> SUCCESS: {reasons_cnt} reasons/versions. GZ: {res.get('gz_size'):,} B, Duration: {round(res.get('duration', 0), 2)}s")

            # Invariant sample check
            if not verify_sample(act_id, pcode):
                print(f"[STOP-LOSS] Sample verification failed for {act_id}!")
                sys.exit(4)

        except Exception as e:
            print(f"  -> EXCEPTION on {name}: {e}")
            with open(FAILED_LOG, "a", encoding="utf-8") as f:
                f.write(f"{act_id},{pcode},{name},exception:{str(e)}\n")
            failed += 1

    batch_duration = time.time() - batch_start
    total_processed = succeeded + no_history + failed
    failure_rate = (failed / total_processed) * 100 if total_processed > 0 else 0

    print(f"\n--- Batch {batch_num} Summary ---")
    print(f"Duration: {round(batch_duration, 1)}s, Requests: {batch_reqs}")
    print(f"Succeeded: {succeeded}, No History Link: {no_history}, Failed: {failed}")
    print(f"Failure rate: {round(failure_rate, 2)}%")

    if failure_rate > 5.0 and failed > 2:
        print(f"[STOP-LOSS] Batch failure rate {round(failure_rate, 2)}% exceeds 5%! Halting.")
        sys.exit(5)

    # Run Check 9 verification
    print("\nVerifying Check 9 verbatim provenance on database...")
    from scripts.verify_integrity import check_lis_data_authenticity
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    if not check_lis_data_authenticity(conn):
        print("[STOP-LOSS] Check 9 failed after batch! Halting.")
        sys.exit(6)
    conn.close()

    # Update progress markdown
    update_progress_report(batch_num, len(acts), succeeded, no_history, failed, total_reasons, batch_duration, batch_reqs)

    # Synchronize batch to remote server
    print("\nSynchronizing batch data to remote server (ubuntu@161.33.166.144)...")
    try:
        from scripts.sync_lis_to_remote import main as sync_remote
        sync_remote()
        print("Remote sync completed successfully.")
    except Exception as e:
        print(f"Warning: Remote sync encountered error: {e}")

    return {
        "batch": batch_num,
        "succeeded": succeeded,
        "no_history": no_history,
        "failed": failed,
        "reasons": total_reasons,
        "duration": batch_duration
    }

def update_progress_report(batch_num, total_in_batch, succeeded, no_history, failed, reasons, duration, reqs):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(DISTINCT act_id), COUNT(1) FROM article_reasons")
    total_db_acts, total_db_reasons = cur.fetchone()
    cur.execute("SELECT COUNT(DISTINCT act_id), COUNT(1) FROM article_versions")
    total_db_v_acts, total_db_versions = cur.fetchone()
    cur.execute("SELECT COUNT(1) FROM source_attempts WHERE source = 'lis'")
    total_attempts = cur.fetchone()[0]
    conn.close()

    header = ""
    if not os.path.exists(PROGRESS_MD):
        header = """# LIS 全法規立法理由與沿革批次爬取進度報告

| 批次 | 法規數 | 成功入庫 | 無沿革頁 (no_data) | 失敗 | 新增理由數 | 耗時 (秒) | 累積資料庫法規數 | 累積理由數 | 累積版本數 | 更新時間 |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
"""
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    row = f"| Batch {batch_num} | {total_in_batch} | {succeeded} | {no_history} | {failed} | {reasons} | {round(duration, 1)}s | {total_db_acts} | {total_db_reasons:,} | {total_db_versions:,} | {now_str} |\n"

    with open(PROGRESS_MD, "a", encoding="utf-8") as f:
        if header:
            f.write(header)
        f.write(row)
    print(f"Updated {PROGRESS_MD}")

def main():
    parser = argparse.ArgumentParser(description="LIS Rollout Runner")
    parser.add_argument("--batch", type=str, default="1", help="Batch number (1..14) or 'all'")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size (default 100)")
    args = parser.parse_args()

    manifest = get_full_manifest()
    # Filter to remaining uncompleted
    remaining = [m for m in manifest if not is_already_done(m["act_id"], m["pcode"])]
    print(f"Total laws: {len(manifest)}, Remaining to crawl: {len(remaining)}")

    batches = [remaining[i:i + args.batch_size] for i in range(0, len(remaining), args.batch_size)]
    print(f"Created {len(batches)} batches of up to {args.batch_size} laws.")

    crawler = LisCrawler()

    if args.batch == "all":
        for b_idx, b_acts in enumerate(batches):
            run_batch(b_idx + 1, b_acts, crawler)
    else:
        b_target = int(args.batch)
        if b_target < 1 or b_target > len(batches):
            print(f"Invalid batch number {b_target}. Must be 1..{len(batches)}")
            sys.exit(1)
        run_batch(b_target, batches[b_target - 1], crawler)

if __name__ == "__main__":
    main()

