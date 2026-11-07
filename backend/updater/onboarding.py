"""
backend/updater/onboarding.py

New Act Onboarding Pipeline (Prompt 4C Part 3):
- Single act onboarding transaction with isolated rollback
- Check 1 immediate verbatim verification
- FTS5 re-indexing
- Downstream queues initialization to not_attempted (law_map, pending_lis)
- Safety valve thresholds: > 5 laws / > 50 orders requires --confirm-add
- 5 Scenario classification: new pcode, rename, pcode shift (pending_human), un-effective, drafts
"""

import os
import sys
import json
import sqlite3
import hashlib
import datetime
from typing import Dict, Any, List, Tuple, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

SLUGS_PATH = os.path.join(BASE_DIR, "config", "slugs.json")
TIERS_PATH = os.path.join(BASE_DIR, "config", "tiers.yaml")

MAX_NEW_LAWS = 5
MAX_NEW_ORDERS = 50


def load_known_slugs() -> Dict[str, str]:
    if os.path.exists(SLUGS_PATH):
        try:
            with open(SLUGS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def normalize_moj_art_no(art_no_str: str) -> str:
    s = art_no_str.replace("第", "").replace("條", "").strip()
    s = s.replace("之", "-")
    return s


def norm_text(txt: str) -> str:
    return (txt or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def check_onboarding_safety_valve(new_laws_count: int, new_orders_count: int, confirm_add: bool = False) -> Tuple[bool, str]:
    """Safety valve: > 5 laws or > 50 orders requires --confirm-add."""
    if new_laws_count > MAX_NEW_LAWS and not confirm_add:
        return False, f"Safety valve triggered: New laws count ({new_laws_count}) exceeds threshold ({MAX_NEW_LAWS}). Pass --confirm-add to approve."
    if new_orders_count > MAX_NEW_ORDERS and not confirm_add:
        return False, f"Safety valve triggered: New orders count ({new_orders_count}) exceeds threshold ({MAX_NEW_ORDERS}). Pass --confirm-add to approve."
    return True, "Safety valve passed."


def onboard_single_act(
    law_dict: Dict[str, Any],
    conn: sqlite3.Connection,
    raw_path: str = "",
    source_url: str = "",
    force_check1_pass: bool = False
) -> Tuple[bool, str, Optional[str]]:
    """
    Onboard a single brand-new act into SQLite database atomically.
    Executes Check 1 immediately. If Check 1 fails, rolls back only this act.
    Returns (success, message, act_id).
    """
    cur = conn.cursor()
    law_name = law_dict.get("LawName", "").strip()
    if not law_name:
        return False, "Empty LawName", None

    law_pcode = (law_dict.get("LawPcode") or "").upper().strip()
    if not law_pcode and "PCode=" in law_dict.get("LawURL", ""):
        law_pcode = law_dict.get("LawURL", "").split("PCode=")[-1].upper().strip()

    slugs = load_known_slugs()
    act_id = slugs.get(law_name) or (law_pcode.lower() if law_pcode else f"act_{hashlib.md5(law_name.encode()).hexdigest()[:8]}")

    abandon_note = (law_dict.get("LawAbandonNote") or "").strip()
    effective_date = (law_dict.get("LawEffectiveDate") or "").strip()
    effective_note = (law_dict.get("LawEffectiveNote") or "").strip()
    modified_date = (law_dict.get("LawModifiedDate") or "").strip()
    category = law_dict.get("LawCategory", "")
    foreword = (law_dict.get("LawForeword") or "").strip()
    history_raw = law_dict.get("LawHistories", "")
    history_json = json.dumps([h.strip() for h in history_raw.split("\r\n") if h.strip()] if history_raw else [], ensure_ascii=False)
    
    # Check if act is abolished from source
    is_abolished = bool(abandon_note) or ("廢止法規" in category)
    act_status = "abolished" if is_abolished else "active"
    first_seen_at = datetime.datetime.now().isoformat()

    # Calculate content hash of the entire act payload
    content_hash = hashlib.sha256(json.dumps(law_dict, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()

    savepoint_name = f"sp_onboard_{act_id.replace('-', '_')}"
    cur.execute(f"SAVEPOINT {savepoint_name}")

    try:
        # 1. Insert Act
        cur.execute("""
            INSERT INTO acts (
                id, pcode, name, name_en, category, last_modified, status,
                effective_date, effective_note, abandon_note,
                effective_raw, effective_note_raw, history_json,
                first_seen_at, source_url, raw_path, content_hash, foreword
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                pcode = excluded.pcode,
                name = excluded.name,
                category = excluded.category,
                last_modified = excluded.last_modified,
                status = excluded.status,
                effective_date = excluded.effective_date,
                effective_note = excluded.effective_note,
                abandon_note = excluded.abandon_note,
                effective_raw = excluded.effective_raw,
                effective_note_raw = excluded.effective_note_raw,
                history_json = excluded.history_json,
                first_seen_at = coalesce(acts.first_seen_at, excluded.first_seen_at),
                source_url = excluded.source_url,
                raw_path = excluded.raw_path,
                content_hash = excluded.content_hash,
                foreword = excluded.foreword
        """, (
            act_id, law_pcode, law_name, law_dict.get("EngLawName", ""), category,
            modified_date, act_status, effective_date, effective_note, abandon_note,
            effective_date, effective_note, history_json,
            first_seen_at, source_url, raw_path, content_hash, foreword
        ))

        if foreword:
            cur.execute("""
                INSERT OR REPLACE INTO act_forewords (act_id, pcode, content, content_hash)
                VALUES (?, ?, ?, ?)
            """, (act_id, law_pcode, foreword, hashlib.sha256(foreword.encode('utf-8')).hexdigest()))

        # 2. Insert Articles
        inserted_articles = []
        for a_obj in law_dict.get("LawArticles", []):
            if a_obj.get("ArticleType") != "A":
                continue
            raw_art_no = a_obj.get("ArticleNo", "")
            art_no = normalize_moj_art_no(raw_art_no)
            if not art_no:
                continue
            
            raw_c = a_obj.get("ArticleContent", "")
            norm_c = norm_text(raw_c)
            # Retain deleted status if content says （刪除）
            art_status = "deleted" if ("（刪除）" in norm_c or "(刪除)" in norm_c) else "active"

            cur.execute("""
                INSERT INTO articles (act_id, article_no, content, status, stale)
                VALUES (?, ?, ?, ?, 0)
                ON CONFLICT(act_id, article_no) DO UPDATE SET
                    content = excluded.content,
                    status = excluded.status,
                    stale = 0
            """, (act_id, art_no, norm_c, art_status))
            inserted_articles.append((art_no, norm_c))

        # 3. Check 1 immediate verbatim fidelity verification
        if not force_check1_pass:
            for art_no, expected_c in inserted_articles:
                cur.execute("SELECT content FROM articles WHERE act_id = ? AND article_no = ?", (act_id, art_no))
                row = cur.fetchone()
                if not row or norm_text(row[0]) != expected_c:
                    cur.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
                    return False, f"Check 1 verification failed for {act_id} art {art_no}: DB content does not match source.", act_id

        # 4. FTS Re-index
        cur.execute("DELETE FROM articles_fts WHERE act_id = ?", (act_id,))
        cur.execute("""
            INSERT INTO articles_fts (act_id, article_no, title, content)
            SELECT act_id, article_no, coalesce(title, ''), content
            FROM articles
            WHERE act_id = ? AND status != 'deleted'
        """, (act_id,))

        # 5. Initialize downstream queues to not_attempted
        # LawPlayer queue: law_map with checked_at = '' (not attempted)
        cur.execute("""
            INSERT INTO law_map (pcode, act_id, lp_act_url, lp_name, matched_by, checked_at, not_found_at)
            VALUES (?, ?, '', ?, 'pending_match', '', NULL)
            ON CONFLICT(pcode) DO UPDATE SET
                act_id = excluded.act_id,
                lp_name = excluded.lp_name
        """, (law_pcode, act_id, law_name))

        # LIS queue: pending_lis (only for primary statutes, orders are not_applicable)
        is_order = ("命令" in category) or ("行政規則" in category)
        if not is_order:
            for art_no, _ in inserted_articles:
                cur.execute("""
                    INSERT INTO pending_lis (act_id, article_no, detected_at, retry_count, status)
                    VALUES (?, ?, ?, 0, 'pending')
                    ON CONFLICT(act_id, article_no) DO NOTHING
                """, (act_id, art_no, first_seen_at))

        cur.execute(f"RELEASE SAVEPOINT {savepoint_name}")
        return True, f"Successfully onboarded act '{law_name}' ({act_id}) with {len(inserted_articles)} articles.", act_id

    except Exception as e:
        cur.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
        return False, f"Exception during onboarding act '{law_name}': {str(e)}", act_id
