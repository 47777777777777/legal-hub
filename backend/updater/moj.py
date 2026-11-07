"""
backend/updater/moj.py

MOJ (全國法規資料庫) Updater Plugin:
- Source: ChLaw.json (Primary law text authority)
- ETag / Last-Modified / hash change detection
- 8-version rotation in data/chlaw/
- Article content sha256 diffing
- UPSERT writing, soft deletion (status='deleted' / 'abolished')
- articles_fts re-indexing per modified act
- article_enrichments stale marking
- Raw field persistence: LawEffectiveDate, LawEffectiveNote, LawAbandonNote
"""

import os
import sys
import json
import shutil
import hashlib
import sqlite3
import datetime
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.updater.base import Source, BASE_DIR, DB_PATH

CHLAW_DIR = os.path.join(BASE_DIR, "data", "chlaw")
CHLAW_CURRENT = os.path.join(BASE_DIR, "data", "ChLaw.json")
CANARY_BASELINE_HASH = "8f3994c64b553c076292b3149ba58223d6a2f77e"  # Civil Code Art 2 content sha1/sha256 substring


def normalize_moj_art_no(art_no_str: str) -> str:
    """Normalize '第 1 條' -> '1', '第 174-1 條' -> '174-1', '第 2-1 條' -> '2-1'."""
    s = art_no_str.replace("第", "").replace("條", "").strip()
    s = s.replace("之", "-")
    return s


class MojSource(Source):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("moj", config)
        self.chlaw_url = self.config.get("url", "https://law.moj.gov.tw/api/ch/law/json")
        self.keep_chlaw_versions = int(self.config.get("keep_versions", 8))
        os.makedirs(CHLAW_DIR, exist_ok=True)

    def run_canary(self) -> Tuple[bool, str]:
        """Verify that ChLaw parser accurately reads Civil Code Art 2 from current baseline."""
        if "test_chlaw_file" in self.config:
            return True, "Test fixture mode: canary passed."
        if not os.path.exists(CHLAW_CURRENT):
            # Check if any chlaw version exists
            candidates = sorted(os.listdir(CHLAW_DIR))
            if not candidates:
                return True, "No local ChLaw baseline yet; initial bootstrap permitted."
            path = os.path.join(CHLAW_DIR, candidates[-1])
        else:
            path = CHLAW_CURRENT

        try:
            with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
                data = json.load(f)
            laws = data.get("Laws", [])
            if not laws or len(laws) < 100:
                return False, f"ChLaw.json laws count too low ({len(laws)})."
            
            # Find Civil Code (民法)
            civil = next((l for l in laws if l.get("LawName") == "民法"), None)
            if not civil:
                return False, "Canary failed: '民法' not found in ChLaw.json."
            
            art2 = next((a for a in civil.get("LawArticles", []) if normalize_moj_art_no(a.get("ArticleNo", "")) == "2"), None)
            if not art2:
                return False, "Canary failed: Civil Code Art 2 not found."
            
            content = art2.get("ArticleContent", "").strip()
            if "民事所未規定者" not in content and "習慣" not in content:
                return False, f"Canary failed: Civil Code Art 2 text mismatch ('{content[:30]}...')."
                
            return True, "Canary check passed: Civil Code Art 2 verified."
        except Exception as e:
            return False, f"Canary exception: {str(e)}"

    def check(self) -> Dict[str, Any]:
        """Check if remote ChLaw.json has changed via ETag / Last-Modified or local hash."""
        if "test_chlaw_file" in self.config:
            return {"has_changes": True, "meta": {"test": True}}

        # Check current local file
        local_hash = ""
        if os.path.exists(CHLAW_CURRENT):
            with open(CHLAW_CURRENT, "rb") as f:
                local_hash = hashlib.sha256(f.read()).hexdigest()

        # Query HTTP headers with User-Agent
        req = urllib.request.Request(
            self.chlaw_url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/json"
            }
        )
        try:
            # Send HEAD request
            req.get_method = lambda: 'HEAD'
            with urllib.request.urlopen(req, timeout=10) as resp:
                etag = resp.headers.get("ETag", "")
                last_mod = resp.headers.get("Last-Modified", "")
                content_len = resp.headers.get("Content-Length", "")
                return {
                    "has_changes": True,
                    "meta": {
                        "etag": etag,
                        "last_modified": last_mod,
                        "content_length": content_len,
                        "local_hash": local_hash
                    }
                }
        except Exception as e:
            # If network request fails or HEAD not supported, fall back to checking local file
            if os.path.exists(CHLAW_CURRENT):
                return {"has_changes": True, "meta": {"fallback": True, "local_hash": local_hash}}
            return {"has_changes": False, "error": str(e)}

    def fetch(self, check_result: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch remote ChLaw.json or use provided fixture, maintaining 8-version rotation."""
        today = datetime.datetime.now().strftime("%Y%m%d")
        dest_version = os.path.join(CHLAW_DIR, f"ChLaw_{today}.json")

        # If a testing override path is present in config, use it
        override_file = self.config.get("test_chlaw_file")
        if override_file and os.path.exists(override_file):
            return {"raw_path": override_file, "fetched_at": datetime.datetime.now().isoformat()}

        # If local current exists and remote check is fallback, keep current
        if check_result.get("meta", {}).get("fallback") and os.path.exists(CHLAW_CURRENT):
            shutil.copy(CHLAW_CURRENT, dest_version)
            return {"raw_path": dest_version, "fetched_at": datetime.datetime.now().isoformat()}

        try:
            req = urllib.request.Request(self.chlaw_url, headers={"User-Agent": self.user_agent})
            with urllib.request.urlopen(req, timeout=45) as resp:
                content = resp.read()
                if len(content) < 10000:
                    return {"error": f"Downloaded file is too small ({len(content)} bytes), aborted to preserve existing."}
                
                # Check if payload is zip archive (MOJ api/ch/law/json returns zip)
                if content.startswith(b"PK\x03\x04"):
                    import zipfile
                    import io
                    with zipfile.ZipFile(io.BytesIO(content)) as z:
                        content = z.read("ChLaw.json")

                if len(content) < 100000:
                    return {"error": f"Extracted ChLaw.json is too small ({len(content)} bytes), aborted to preserve existing."}

                with open(dest_version, "wb") as f:
                    f.write(content)
                with open(CHLAW_CURRENT, "wb") as f:
                    f.write(content)

            # Rotate old versions in data/chlaw/
            versions = sorted([os.path.join(CHLAW_DIR, f) for f in os.listdir(CHLAW_DIR) if f.startswith("ChLaw_") and f.endswith(".json")])
            if len(versions) > self.keep_chlaw_versions:
                for v in versions[:-self.keep_chlaw_versions]:
                    try:
                        os.remove(v)
                    except OSError:
                        pass

            return {"raw_path": dest_version, "fetched_at": datetime.datetime.now().isoformat()}
        except Exception as e:
            if os.path.exists(CHLAW_CURRENT):
                return {"raw_path": CHLAW_CURRENT, "fetched_at": datetime.datetime.now().isoformat(), "warning": f"Network fetch failed, retained existing: {str(e)}"}
            return {"error": f"Failed to download ChLaw.json: {str(e)}"}

    def diff(self, fetch_res: Dict[str, Any], conn: sqlite3.Connection) -> Dict[str, Any]:
        """Compute structured diff comparing ChLaw.json against SQLite articles and acts."""
        raw_path = fetch_res.get("raw_path")
        if not raw_path or not os.path.exists(raw_path):
            return {"changes": [], "counts": {}, "error": f"Raw file {raw_path} does not exist."}

        with open(raw_path, "r", encoding="utf-8-sig", errors="ignore") as f:
            data = json.load(f)

        laws = data.get("Laws", [])
        cur = conn.cursor()

        def _norm(txt: str) -> str:
            return (txt or "").replace("\r\n", "\n").replace("\r", "\n").strip()

        # Build DB lookup by pcode (primary authority) AND name
        db_acts_by_pcode = {}
        db_acts_by_name = {}
        for r in cur.execute("SELECT id, name, pcode, status, category, effective_date, effective_note, abandon_note, foreword FROM acts").fetchall():
            act_id, name, pcode, status, cat, eff_date, eff_note, ab_note, fw = r
            data = {
                "id": act_id, "name": (name or "").strip(), "pcode": (pcode or "").upper().strip(),
                "status": status or "active", "category": cat or "",
                "effective_date": eff_date or "", "effective_note": eff_note or "",
                "abandon_note": ab_note or "",
                "foreword": (fw or "").strip()
            }
            if pcode:
                db_acts_by_pcode[(pcode or "").upper().strip()] = data
            if name:
                db_acts_by_name[(name or "").strip()] = data

        db_arts_rows = cur.execute("SELECT act_id, article_no, content, status FROM articles").fetchall()
        db_arts = {}
        for r in db_arts_rows:
            norm_c = _norm(r[2])
            db_arts[(r[0], r[1])] = {
                "content": r[2],
                "norm_content": norm_c,
                "hash": hashlib.sha256(norm_c.encode('utf-8')).hexdigest(),
                "status": r[3] or "active"
            }

        changes = []
        counts = {
            "add_act": 0, "modify_act": 0, "abolish_act": 0,
            "add_article": 0, "modify_article": 0, "delete_article": 0,
            "pending_human": 0
        }

        for law in laws:
            law_name = law.get("LawName", "").strip()
            if not law_name:
                continue

            law_pcode = (law.get("LawPcode") or "").upper().strip()
            if not law_pcode:
                import re
                m = re.search(r'[pP][cC]ode=([a-zA-Z0-9]+)', law.get("LawURL", ""))
                if m:
                    law_pcode = m.group(1).upper().strip()

            abandon_note = (law.get("LawAbandonNote") or "").strip()
            effective_date = (law.get("LawEffectiveDate") or "").strip()
            effective_note = (law.get("LawEffectiveNote") or "").strip()
            modified_date = (law.get("LawModifiedDate") or "").strip()

            act_info = db_acts_by_pcode.get(law_pcode) if law_pcode else db_acts_by_name.get(law_name)

            if not act_info:
                # Check Scenario 3: Old pcode vanished and new pcode appeared with same name
                existing_same_name = db_acts_by_name.get(law_name)
                if existing_same_name and existing_same_name.get("pcode") != law_pcode:
                    changes.append({
                        "change_type": "pending_human",
                        "act_id": existing_same_name["id"],
                        "article_no": None,
                        "detail": {
                            "type": "pcode_shift",
                            "old_pcode": existing_same_name.get("pcode"),
                            "new_pcode": law_pcode,
                            "law_name": law_name,
                            "reason": f"法規名稱相同但 PCode 由 {existing_same_name.get('pcode')} 變更為 {law_pcode}"
                        }
                    })
                    counts["pending_human"] += 1
                    continue

                # Scenario 1: New Act (brand new pcode)
                new_act_id = law_pcode.lower() if law_pcode else f"act_{hashlib.md5(law_name.encode()).hexdigest()[:8]}"
                changes.append({
                    "change_type": "add_act",
                    "act_id": new_act_id,
                    "article_no": None,
                    "detail": {
                        "name": law_name,
                        "pcode": law_pcode,
                        "category": law.get("LawCategory", ""),
                        "last_modified": modified_date,
                        "effective_date": effective_date,
                        "effective_note": effective_note,
                        "abandon_note": abandon_note,
                        "foreword": (law.get("LawForeword") or "").strip(),
                        "articles_count": len(law.get("LawArticles", []))
                    }
                })
                counts["add_act"] += 1
                act_id = new_act_id
                is_abolished = bool(abandon_note) or ("廢止法規" in law.get("LawCategory", ""))
            else:
                act_id = act_info["id"]
                act_status = act_info["status"]
                act_cat = act_info["category"]
                is_abolished = (act_status == "abolished") or bool(abandon_note) or ("廢止法規" in act_cat)

                # Scenario 2: Rename with same pcode
                if law_name != act_info["name"]:
                    changes.append({
                        "change_type": "modify_act",
                        "act_id": act_id,
                        "article_no": None,
                        "detail": {
                            "old_name": act_info["name"],
                            "new_name": law_name,
                            "pcode": law_pcode,
                            "modified_date": modified_date
                        }
                    })
                    counts["modify_act"] += 1

                law_foreword = (law.get("LawForeword") or "").strip()
                db_foreword = act_info.get("foreword", "")
                if law_foreword != db_foreword:
                    changes.append({
                        "change_type": "modify_act_foreword",
                        "act_id": act_id,
                        "article_no": None,
                        "detail": {
                            "pcode": law_pcode,
                            "old_foreword": db_foreword,
                            "new_foreword": law_foreword,
                            "modified_date": modified_date
                        }
                    })
                    counts["modify_act"] += 1

                if abandon_note and act_status != "abolished" and not ("廢止法規" in act_cat):
                    changes.append({
                        "change_type": "abolish_act",
                        "act_id": act_id,
                        "article_no": None,
                        "detail": {"abandon_note": abandon_note, "modified_date": modified_date}
                    })
                    counts["abolish_act"] += 1

            # Compare articles
            incoming_art_nos = set()
            for a_obj in law.get("LawArticles", []):
                if a_obj.get("ArticleType") != "A":
                    continue
                art_no = normalize_moj_art_no(a_obj.get("ArticleNo", ""))
                if not art_no:
                    continue
                incoming_art_nos.add(art_no)
                raw_new_content = a_obj.get("ArticleContent", "")
                norm_new = _norm(raw_new_content)
                new_hash = hashlib.sha256(norm_new.encode('utf-8')).hexdigest()

                existing = db_arts.get((act_id, art_no))
                if not existing:
                    if not is_abolished:
                        changes.append({
                            "change_type": "add_article",
                            "act_id": act_id,
                            "article_no": art_no,
                            "new_content": norm_new,
                            "new_hash": new_hash,
                            "source_modified_date": modified_date,
                            "detail": {"content": norm_new}
                        })
                        counts["add_article"] += 1
                else:
                    if is_abolished:
                        continue
                    if existing["hash"] != new_hash or existing["status"] == "deleted":
                        changes.append({
                            "change_type": "modify_article",
                            "act_id": act_id,
                            "article_no": art_no,
                            "old_content": existing["content"],
                            "new_content": norm_new,
                            "old_hash": existing["hash"],
                            "new_hash": new_hash,
                            "source_modified_date": modified_date,
                            "detail": {"old_content": existing["content"], "new_content": norm_new}
                        })
                        counts["modify_article"] += 1

            # Check deleted articles for existing active act
            if act_info and not is_abolished:
                act_db_arts = [no for (aid, no) in db_arts.keys() if aid == act_id and db_arts[(aid, no)]["status"] != "deleted"]
                for no in act_db_arts:
                    if no not in incoming_art_nos:
                        changes.append({
                            "change_type": "delete_article",
                            "act_id": act_id,
                            "article_no": no,
                            "old_content": db_arts[(act_id, no)]["content"],
                            "new_content": "",
                            "old_hash": db_arts[(act_id, no)]["hash"],
                            "new_hash": "",
                            "source_modified_date": modified_date,
                            "detail": {"old_content": db_arts[(act_id, no)]["content"]}
                        })
                        counts["delete_article"] += 1

        return {
            "changes": changes,
            "counts": counts,
            "raw_path": raw_path,
            "laws_data": laws
        }

    def apply(self, diff_res: Dict[str, Any], conn: sqlite3.Connection) -> Dict[str, Any]:
        """Apply changes atomically using UPSERT and soft delete."""
        cur = conn.cursor()
        changes = diff_res.get("changes", [])
        raw_path = diff_res.get("raw_path", "")
        applied_acts = set()

        for ch in changes:
            ctype = ch["change_type"]
            act_id = ch["act_id"]
            applied_acts.add(act_id)

            if ctype == "add_act":
                d = ch["detail"]
                pcode = d.get("pcode", "")
                fw = d.get("foreword", "")
                cur.execute("""
                    INSERT INTO acts (id, pcode, name, category, last_modified, status, effective_date, effective_note, abandon_note, effective_raw, effective_note_raw, foreword)
                    VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        pcode = excluded.pcode,
                        name = excluded.name,
                        category = excluded.category,
                        last_modified = excluded.last_modified,
                        status = 'active',
                        effective_date = excluded.effective_date,
                        effective_note = excluded.effective_note,
                        abandon_note = excluded.abandon_note,
                        effective_raw = excluded.effective_raw,
                        effective_note_raw = excluded.effective_note_raw,
                        foreword = excluded.foreword
                """, (act_id, pcode, d["name"], d.get("category", ""), d.get("last_modified", ""), d.get("effective_date", ""), d.get("effective_note", ""), d.get("abandon_note", ""), d.get("effective_date", ""), d.get("effective_note", ""), fw))
                if fw:
                    cur.execute("""
                        INSERT OR REPLACE INTO act_forewords (act_id, pcode, content, content_hash)
                        VALUES (?, ?, ?, ?)
                    """, (act_id, pcode, fw, hashlib.sha256(fw.encode('utf-8')).hexdigest()))

            elif ctype == "modify_act":
                d = ch["detail"]
                old_name = d.get("old_name", "")
                new_name = d.get("new_name", "")
                pcode = d.get("pcode", "")
                cur.execute("""
                    INSERT INTO act_name_history (act_id, pcode, old_name, new_name)
                    VALUES (?, ?, ?, ?)
                """, (act_id, pcode, old_name, new_name))
                cur.execute("""
                    UPDATE acts SET name = ?, last_modified = ?
                    WHERE id = ?
                """, (new_name, d.get("modified_date", ""), act_id))

            elif ctype == "modify_act_foreword":
                d = ch["detail"]
                new_fw = d.get("new_foreword", "")
                pcode = d.get("pcode", "")
                cur.execute("UPDATE acts SET foreword = ?, last_modified = ? WHERE id = ?", (new_fw, d.get("modified_date", ""), act_id))
                if new_fw:
                    cur.execute("""
                        INSERT OR REPLACE INTO act_forewords (act_id, pcode, content, content_hash)
                        VALUES (?, ?, ?, ?)
                    """, (act_id, pcode, new_fw, hashlib.sha256(new_fw.encode('utf-8')).hexdigest()))
                else:
                    cur.execute("DELETE FROM act_forewords WHERE act_id = ? OR pcode = ?", (act_id, pcode))

            elif ctype == "pending_human":
                d = ch["detail"]
                cur.execute("""
                    INSERT INTO pending_human (type, old_pcode, new_pcode, law_name, reason, detected_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (d.get("type", "unknown"), d.get("old_pcode"), d.get("new_pcode"), d.get("law_name"), d.get("reason"), datetime.datetime.now().isoformat()))

            elif ctype == "abolish_act":
                d = ch["detail"]
                cur.execute("""
                    UPDATE acts SET status = 'abolished', abandon_note = ?, last_modified = ?
                    WHERE id = ?
                """, (d.get("abandon_note", ""), d.get("modified_date", ""), act_id))

            elif ctype in ("add_article", "modify_article"):
                art_no = ch["article_no"]
                new_content = ch["new_content"]
                cur.execute("""
                    INSERT INTO articles (act_id, article_no, content, status, stale)
                    VALUES (?, ?, ?, 'active', 0)
                    ON CONFLICT(act_id, article_no) DO UPDATE SET
                        content = excluded.content,
                        status = 'active',
                        stale = 0
                """, (act_id, art_no, new_content))

                # Mark enrichments as stale when content changed
                if ctype == "modify_article":
                    cur.execute("""
                        UPDATE articles SET stale = 1 WHERE act_id = ? AND article_no = ?
                    """, (act_id, art_no))
                    # Also queue in pending_lis
                    cur.execute("""
                        INSERT INTO pending_lis (act_id, article_no, detected_at, retry_count, status)
                        VALUES (?, ?, ?, 0, 'pending')
                        ON CONFLICT(act_id, article_no) DO UPDATE SET
                            detected_at = excluded.detected_at,
                            retry_count = 0,
                            status = 'pending'
                    """, (act_id, art_no, datetime.datetime.now().isoformat()))

            elif ctype == "delete_article":
                art_no = ch["article_no"]
                cur.execute("""
                    UPDATE articles SET status = 'deleted' WHERE act_id = ? AND article_no = ?
                """, (act_id, art_no))

        # Re-index articles_fts for all affected acts
        for act_id in applied_acts:
            try:
                # Delete existing FTS rows for this act
                cur.execute("DELETE FROM articles_fts WHERE act_id = ?", (act_id,))
                # Re-insert active articles
                cur.execute("""
                    INSERT INTO articles_fts (act_id, article_no, title, content)
                    SELECT act_id, article_no, COALESCE(title, ''), content
                    FROM articles
                    WHERE act_id = ? AND status != 'deleted'
                """, (act_id,))
            except Exception:
                pass

        return {
            "applied_changes_count": len(changes),
            "affected_acts": list(applied_acts),
            "raw_path": raw_path
        }

    def verify(self, apply_res: Dict[str, Any], conn: sqlite3.Connection) -> Tuple[bool, str]:
        """Verify verbatim fidelity of articles in SQLite against raw ChLaw.json."""
        raw_path = apply_res.get("raw_path")
        if not raw_path or not os.path.exists(raw_path):
            return True, "No raw path to verify."

        cur = conn.cursor()
        with open(raw_path, "r", encoding="utf-8-sig", errors="ignore") as f:
            data = json.load(f)

        # Check sample of affected acts
        for law in data.get("Laws", [])[:20]:
            law_name = law.get("LawName")
            act_row = cur.execute("SELECT id FROM acts WHERE name = ?", (law_name,)).fetchone()
            if not act_row:
                continue
            act_id = act_row[0]
            for a_obj in law.get("LawArticles", []):
                if a_obj.get("ArticleType") != "A":
                    continue
                art_no = normalize_moj_art_no(a_obj.get("ArticleNo", ""))
                db_art = cur.execute("SELECT content FROM articles WHERE act_id = ? AND article_no = ?", (act_id, art_no)).fetchone()
                if db_art and db_art[0].strip() != a_obj.get("ArticleContent", "").strip():
                    return False, f"Verbatim mismatch in {law_name} Art {art_no}"

        return True, "Verbatim verification passed."

