"""
backend/updater/lis.py

LIS (立法院法律系統) Legislative Reasons Updater Plugin:
- Source: lis.ly.gov.tw (Full-act reasons & comparison tables)
- Canary validation against APA Art 1 baseline
- Weekly rotation & pending_lis queue processing
- Historical immutability assertion (aborts if past versions changed)
- Check 9 verbatim provenance verification
- 8-week pending_lis expiry management
"""

import os
import sys
import json
import sqlite3
import datetime
from typing import Dict, Any, List, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.updater.base import Source, BASE_DIR, DB_PATH
from backend.lis.parser import parse_full_act_reasons, parse_comparisons_from_html

SAMPLES_DIR = os.path.join(BASE_DIR, "data", "raw", "lis", "samples")
CANARY_FILE = os.path.join(SAMPLES_DIR, "sample_1.html")


SLUGS_PATH = os.path.join(BASE_DIR, "config", "slugs.json")

def get_configured_slug(law_name: str, fallback: str) -> str:
    if os.path.exists(SLUGS_PATH):
        try:
            with open(SLUGS_PATH, "r", encoding="utf-8") as f:
                return json.load(f).get(law_name, fallback)
        except Exception:
            pass
    return fallback

class LisSource(Source):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("lis", config)
        self.portal_url = "https://lis.ly.gov.tw/lglawc/lglawkm"
        self.default_pilot_id = get_configured_slug("行政程序法", "A0030109")

    def run_canary(self) -> Tuple[bool, str]:
        """Verify that LIS parser correctly parses APA Art 1 reasons from baseline."""
        if not os.path.exists(CANARY_FILE):
            return True, "No local LIS baseline sample; bootstrap permitted."
            
        try:
            with open(CANARY_FILE, "rb") as f:
                raw_bytes = f.read()
            try:
                content = raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                content = raw_bytes.decode("big5", errors="ignore")

            results = parse_full_act_reasons(content)
            if not results:
                return False, "Canary failed: parse_full_act_reasons returned 0 items."
            
            art1 = next((r for r in results if r["article_no"] == "1"), None)
            if not art1 or "本條明定本法之立法目的" not in art1["reason"]:
                return False, "Canary failed: APA Art 1 reason text mismatch."
                
            return True, "Canary check passed: APA Art 1 verified."
        except Exception as e:
            return False, f"Canary exception: {str(e)}"

    def check(self) -> Dict[str, Any]:
        """Check for pending_lis items or acts requiring LIS updates."""
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        # Check pending_lis queue
        pending_rows = cur.execute("""
            SELECT id, act_id, article_no, detected_at, retry_count
            FROM pending_lis
            WHERE status = 'pending'
        """).fetchall()
        
        # Check if testing override is active
        override_file = self.config.get("test_lis_file")
        if override_file and os.path.exists(override_file):
            conn.close()
            return {"has_changes": True, "meta": {"test_override": override_file, "pending_count": len(pending_rows)}}

        # Check APA status in article_reasons
        apa_count = cur.execute("SELECT count(*) FROM article_reasons WHERE act_id = ?", (self.default_pilot_id,)).fetchone()[0]
        conn.close()

        has_changes = len(pending_rows) > 0 or apa_count == 0
        return {
            "has_changes": has_changes,
            "meta": {
                "pending_count": len(pending_rows),
                "apa_reasons_count": apa_count
            }
        }

    def fetch(self, check_res: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch raw HTML for full act reasons (using live session or test fixture)."""
        override_file = self.config.get("test_lis_file")
        if override_file and os.path.exists(override_file):
            return {
                "raw_path": override_file,
                "act_id": self.config.get("test_act_id", self.default_pilot_id),
                "fetched_at": datetime.datetime.now().isoformat()
            }

        # Use canonical sample_1 if existing for APA dry-run / sync
        if os.path.exists(CANARY_FILE):
            return {
                "raw_path": CANARY_FILE,
                "act_id": self.default_pilot_id,
                "fetched_at": "2026-11-03"
            }

        return {"error": "LIS automated web fetch requires active browser session."}

    def diff(self, fetch_res: Dict[str, Any], conn: sqlite3.Connection) -> Dict[str, Any]:
        """Diff parsed LIS reasons against existing article_reasons records."""
        raw_path = fetch_res.get("raw_path")
        act_id = fetch_res.get("act_id", self.default_pilot_id)
        if not raw_path or not os.path.exists(raw_path):
            return {"changes": [], "counts": {}, "error": f"Raw file {raw_path} does not exist."}

        with open(raw_path, "rb") as f:
            raw_bytes = f.read()
        try:
            html = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            html = raw_bytes.decode("big5", errors="ignore")

        parsed_items = parse_full_act_reasons(html, raw_path=raw_path)
        cur = conn.cursor()

        # Query existing DB versions for this act
        cur.execute("""
            SELECT article_no, version_date, reason, date_label_raw
            FROM article_reasons
            WHERE act_id = ?
        """, (act_id,))
        existing_versions = {}
        for r in cur.fetchall():
            existing_versions[(r[0], r[1])] = {
                "reason": r[2] or "",
                "date_label": r[3] or ""
            }

        changes = []
        counts = {"new_version": 0, "unchanged_version": 0}

        for item in parsed_items:
            art_no = item["article_no"]
            v_date = item["version_date"]
            key = (art_no, v_date)

            if key not in existing_versions:
                changes.append({
                    "change_type": "add_reason_version",
                    "act_id": act_id,
                    "article_no": art_no,
                    "version_date": v_date,
                    "new_content": item["reason"],
                    "old_content": "",
                    "new_hash": "",
                    "old_hash": "",
                    "detail": item
                })
                counts["new_version"] += 1
            else:
                # IMMUTABILITY CHECK: Previous historical reasons must not silently mutate!
                old_reason = existing_versions[key]["reason"].strip().replace("\r\n", "\n")
                new_reason = item["reason"].strip().replace("\r\n", "\n")
                if old_reason != new_reason:
                    return {
                        "changes": [],
                        "counts": counts,
                        "error": f"Historical immutability violation: Art {art_no} version {v_date} reason altered in source!"
                    }
                counts["unchanged_version"] += 1

        return {
            "changes": changes,
            "counts": counts,
            "raw_path": raw_path,
            "act_id": act_id
        }

    def apply(self, diff_res: Dict[str, Any], conn: sqlite3.Connection) -> Dict[str, Any]:
        """Apply new reason versions and update pending_lis queue."""
        cur = conn.cursor()
        changes = diff_res.get("changes", [])
        act_id = diff_res.get("act_id")

        inserted = 0
        for ch in changes:
            d = ch["detail"]
            cur.execute("""
                INSERT INTO article_reasons (
                    act_id, article_no, version_date, action_type, reason, source, source_url,
                    fetched_at, raw_path, date_label_raw, date_raw, article_no_at_the_time, source_mode
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(act_id, article_no, version_date) DO UPDATE SET
                    reason = excluded.reason,
                    date_label_raw = excluded.date_label_raw
            """, (
                d["act_id"] if "act_id" in d else act_id,
                d["article_no"], d["version_date"], d.get("action_type", ""), d["reason"],
                d.get("source", "立法院法律系統"), d.get("source_url", ""), datetime.datetime.now().isoformat(),
                diff_res.get("raw_path", ""), d.get("date_label_raw", ""), d.get("date_raw", ""),
                d.get("article_no_at_the_time", ""), d.get("source_mode", "fullpage")
            ))
            inserted += 1

            # Remove from pending_lis if resolved
            cur.execute("DELETE FROM pending_lis WHERE act_id = ? AND article_no = ?", (act_id, d["article_no"]))

        # Manage 8-week expiry for unresolved pending_lis items
        cur.execute("""
            UPDATE pending_lis
            SET retry_count = retry_count + 1, last_checked_at = ?
            WHERE status = 'pending'
        """, (datetime.datetime.now().isoformat(),))

        cur.execute("""
            UPDATE pending_lis
            SET status = 'expired_8_weeks'
            WHERE status = 'pending' AND retry_count >= 8
        """)

        return {"inserted_reasons": inserted, "raw_path": diff_res.get("raw_path")}

    def verify(self, apply_res: Dict[str, Any], conn: sqlite3.Connection) -> Tuple[bool, str]:
        """Check 9 verbatim verification on all article_reasons."""
        raw_path = apply_res.get("raw_path")
        if not raw_path or not os.path.exists(raw_path):
            return True, "No raw path to verify."

        cur = conn.cursor()
        rows = cur.execute("SELECT id, act_id, article_no, reason, raw_path FROM article_reasons WHERE raw_path = ?", (raw_path,)).fetchall()
        
        with open(raw_path, "r", encoding="utf-8", errors="ignore") as f:
            clean_raw = "".join(f.read().split())

        for r in rows:
            clean_reason = "".join((r[3] or "").split())
            if clean_reason and clean_reason not in clean_raw:
                return False, f"Check 9 failed: Art {r[2]} reason not verbatim substring of {raw_path}"

        return True, "LIS verbatim verification passed."

