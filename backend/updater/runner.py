"""
backend/updater/runner.py

Orchestrates Source lifecycle execution with strict safety guarantees:
- Canary testing before execution
- Anomaly volume protection
- Automatic 14-run backup
- Transaction isolation & atomic rollback on verify failure
- Run logging in update_runs & update_changes
"""

import os
import sys
import json
import uuid
import yaml
import sqlite3
import datetime
from typing import Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.updater.base import (
    Source,
    backup_database,
    check_anomaly,
    DB_PATH
)
CONFIG_PATH = os.path.join(BASE_DIR, "config", "sources.yaml")
LOG_DIR = os.path.join(BASE_DIR, "logs", "update")


def log_update_message(msg: str):
    """Write update log with 60-day date rotation."""
    os.makedirs(LOG_DIR, exist_ok=True)
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(LOG_DIR, f"{today}.log")
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")
    print(msg)


def execute_update_run(
    source: Source,
    apply: bool = False,
    mode: str = "scheduled",
    conn: Optional[sqlite3.Connection] = None,
    confirm_abolish: bool = False
) -> Dict[str, Any]:
    """
    Executes a complete update cycle for a given Source plugin.
    Defaults to dry-run unless apply=True is explicitly passed.
    """
    own_conn = False
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        own_conn = True

    started_at = datetime.datetime.now().isoformat()
    run_id = f"{source.name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    dry_run_int = 0 if apply else 1
    
    log_update_message(f"=== Starting Update Run [{run_id}] source={source.name} mode={mode} apply={apply} ===")

    # Initial run record
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO update_runs (run_id, source, mode, started_at, status, counts_json, dry_run)
        VALUES (?, ?, ?, ?, 'running', '{}', ?)
    """, (run_id, source.name, mode, started_at, dry_run_int))
    conn.commit()

    try:
        # Step 1: Canary Regression Check
        log_update_message(f"[{source.name}] Step 1: Running canary regression check...")
        canary_ok, canary_msg = source.run_canary()
        if not canary_ok:
            err = f"Canary regression check failed: {canary_msg}"
            log_update_message(f"[{source.name}] ERROR: {err}")
            cur.execute("""
                UPDATE update_runs SET finished_at = ?, status = 'canary_failed', error = ?
                WHERE run_id = ?
            """, (datetime.datetime.now().isoformat(), err, run_id))
            conn.commit()
            return {"run_id": run_id, "status": "canary_failed", "error": err}

        # Step 2: Lightweight Check
        log_update_message(f"[{source.name}] Step 2: Checking remote source for modifications...")
        check_res = source.check()
        if not check_res.get("has_changes"):
            log_update_message(f"[{source.name}] Source has no changes. Ending run.")
            cur.execute("""
                UPDATE update_runs SET finished_at = ?, status = 'no_change', counts_json = ?
                WHERE run_id = ?
            """, (datetime.datetime.now().isoformat(), json.dumps(check_res.get("meta", {})), run_id))
            conn.commit()
            return {"run_id": run_id, "status": "no_change", "meta": check_res.get("meta", {})}

        # Step 3: Fetch Changed Raw Data
        log_update_message(f"[{source.name}] Step 3: Fetching modified raw data...")
        source.throttle()
        fetch_res = source.fetch(check_res)
        if fetch_res.get("error"):
            err = fetch_res["error"]
            log_update_message(f"[{source.name}] Fetch failed: {err}")
            cur.execute("""
                UPDATE update_runs SET finished_at = ?, status = 'fetch_failed', error = ?
                WHERE run_id = ?
            """, (datetime.datetime.now().isoformat(), err, run_id))
            conn.commit()
            return {"run_id": run_id, "status": "fetch_failed", "error": err}

        # Step 4: Diff against Database
        log_update_message(f"[{source.name}] Step 4: Computing diff against database...")
        diff_res = source.diff(fetch_res, conn)
        changes = diff_res.get("changes", [])
        counts = diff_res.get("counts", {})
        log_update_message(f"[{source.name}] Diff computed: {len(changes)} change(s), counts: {counts}")

        if not changes:
            cur.execute("""
                UPDATE update_runs SET finished_at = ?, status = 'no_change', counts_json = ?
                WHERE run_id = ?
            """, (datetime.datetime.now().isoformat(), json.dumps(counts), run_id))
            conn.commit()
            return {"run_id": run_id, "status": "no_change", "counts": counts}

        # Step 4.5: Act Abolition Safety Valve (> 10 acts require --confirm-abolish)
        abolish_count = counts.get("abolish_act", 0)
        if abolish_count > 10 and not confirm_abolish:
            safety_msg = f"Safety valve triggered: Proposed {abolish_count} act abolitions exceeds safety limit of 10. Manual intervention with --confirm-abolish required."
            log_update_message(f"[{source.name}] SAFETY VALVE ABORT TRIGGERED: {safety_msg}")
            cur.execute("""
                UPDATE update_runs SET finished_at = ?, status = 'aborted_safety_valve', error = ?, counts_json = ?
                WHERE run_id = ?
            """, (datetime.datetime.now().isoformat(), safety_msg, json.dumps(counts), run_id))
            for ch in changes[:100]:
                cur.execute("""
                    INSERT INTO update_changes (run_id, source, act_id, article_no, change_type, old_hash, new_hash, detail_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (run_id, source.name, ch.get("act_id"), ch.get("article_no"), "aborted_safety_valve_" + ch.get("change_type", "change"), ch.get("old_hash"), ch.get("new_hash"), json.dumps(ch.get("detail", {}), ensure_ascii=False)))
            conn.commit()
            return {"run_id": run_id, "status": "aborted_safety_valve", "error": safety_msg, "counts": counts}

        # Step 5: Anomaly Volume Protection Check
        log_update_message(f"[{source.name}] Step 5: Checking volume safety thresholds...")
        max_tot = float(source.config.get("max_total_ratio", 0.03))
        max_act = float(source.config.get("max_act_ratio", 0.50))
        is_anomaly, anomaly_msg = check_anomaly(diff_res, conn, max_total_ratio=max_tot, max_act_ratio=max_act)
        if is_anomaly:
            log_update_message(f"[{source.name}] ANOMALY ABORT TRIGGERED: {anomaly_msg}")
            cur.execute("""
                UPDATE update_runs SET finished_at = ?, status = 'aborted_anomaly', error = ?, counts_json = ?
                WHERE run_id = ?
            """, (datetime.datetime.now().isoformat(), anomaly_msg, json.dumps(counts), run_id))
            # Record aborted changes for audit inspection
            for ch in changes[:100]:
                cur.execute("""
                    INSERT INTO update_changes (run_id, source, act_id, article_no, change_type, old_hash, new_hash, detail_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (run_id, source.name, ch.get("act_id"), ch.get("article_no"), "aborted_" + ch.get("change_type", "change"), ch.get("old_hash"), ch.get("new_hash"), json.dumps(ch.get("detail", {}), ensure_ascii=False)))
            conn.commit()
            return {"run_id": run_id, "status": "aborted_anomaly", "error": anomaly_msg, "counts": counts}

        # If Dry Run: log and exit safely without modifying live tables
        if not apply:
            log_update_message(f"[{source.name}] Dry-run requested. Recording planned changes without live write.")
            cur.execute("""
                UPDATE update_runs SET finished_at = ?, status = 'dry_run_completed', counts_json = ?
                WHERE run_id = ?
            """, (datetime.datetime.now().isoformat(), json.dumps(counts), run_id))
            for ch in changes:
                cur.execute("""
                    INSERT INTO update_changes (run_id, source, act_id, article_no, change_type, old_hash, new_hash, detail_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (run_id, source.name, ch.get("act_id"), ch.get("article_no"), ch.get("change_type"), ch.get("old_hash"), ch.get("new_hash"), json.dumps(ch.get("detail", {}), ensure_ascii=False)))
            conn.commit()
            return {"run_id": run_id, "status": "dry_run_completed", "counts": counts, "changes": changes}

        # Step 6: Live Apply with Pre-Backup & Transaction Rollback Protection
        log_update_message(f"[{source.name}] Step 6: Creating pre-write backup...")
        target_db_path = DB_PATH
        try:
            for row in cur.execute("PRAGMA database_list").fetchall():
                if row[1] == "main" and row[2]:
                    target_db_path = row[2]
                    break
        except Exception:
            pass
        backup_path = backup_database(db_path=target_db_path)
        log_update_message(f"[{source.name}] Backup created at: {backup_path}")

        log_update_message(f"[{source.name}] Applying changes inside transaction...")
        # Begin transaction
        cur.execute("BEGIN TRANSACTION")
        apply_res = source.apply(diff_res, conn)

        # Record changes in update_changes and article_revisions
        for ch in changes:
            cur.execute("""
                INSERT INTO update_changes (run_id, source, act_id, article_no, change_type, old_hash, new_hash, detail_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (run_id, source.name, ch.get("act_id"), ch.get("article_no"), ch.get("change_type"), ch.get("old_hash"), ch.get("new_hash"), json.dumps(ch.get("detail", {}), ensure_ascii=False)))
            
            # If revision, record in article_revisions
            if ch.get("change_type") in ("modify", "modify_article", "delete", "delete_article") and ch.get("old_content"):
                cur.execute("""
                    INSERT INTO article_revisions (
                        act_id, article_no, old_content, new_content, old_hash, new_hash,
                        change_type, detected_at, source_modified_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ch.get("act_id"), ch.get("article_no"), ch.get("old_content"), ch.get("new_content"),
                    ch.get("old_hash"), ch.get("new_hash"), ch.get("change_type"),
                    started_at, ch.get("source_modified_date")
                ))

        # Step 7: Immediate Post-Write Verification
        log_update_message(f"[{source.name}] Step 7: Running immediate post-write verification...")
        verify_ok, verify_msg = source.verify(apply_res, conn)
        if not verify_ok:
            log_update_message(f"[{source.name}] VERIFICATION FAILED: {verify_msg}. Rolling back transaction!")
            cur.execute("ROLLBACK")
            cur.execute("""
                UPDATE update_runs SET finished_at = ?, status = 'verify_failed_rolled_back', error = ?
                WHERE run_id = ?
            """, (datetime.datetime.now().isoformat(), verify_msg, run_id))
            conn.commit()
            return {"run_id": run_id, "status": "verify_failed_rolled_back", "error": verify_msg}

        # Step 8: Commit & Finalize
        cur.execute("COMMIT")
        cur.execute("""
            UPDATE update_runs SET finished_at = ?, status = 'success', counts_json = ?
            WHERE run_id = ?
        """, (datetime.datetime.now().isoformat(), json.dumps(counts), run_id))
        conn.commit()
        log_update_message(f"[{source.name}] Update run [{run_id}] succeeded and committed.")

        # Clear in-memory cache
        try:
            from backend.storage import storage
            storage.cache.clear()
            log_update_message(f"[{source.name}] Cleared backend in-memory cache.")
        except Exception:
            pass

        return {"run_id": run_id, "status": "success", "counts": counts, "applied": apply_res}

    except Exception as e:
        conn.rollback()
        err_msg = f"Unexpected exception during update: {str(e)}"
        log_update_message(f"[{source.name}] CRITICAL: {err_msg}")
        try:
            cur.execute("""
                UPDATE update_runs SET finished_at = ?, status = 'exception_rolled_back', error = ?
                WHERE run_id = ?
            """, (datetime.datetime.now().isoformat(), err_msg, run_id))
            conn.commit()
        except Exception:
            pass
        return {"run_id": run_id, "status": "exception_rolled_back", "error": err_msg}

    finally:
        if own_conn:
            conn.close()

