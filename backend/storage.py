"""
Storage repository, duplicate validations, SQLite backing layer, and caching for Legal Hub.
Reconstructs domain models with full LawPlayer enrichments via LEFT JOIN.
"""
import os
import json
import time
import sqlite3
from typing import Dict, List, Optional, Any
from backend.models import Act, Article, Attachment, Literature, ValidationError
from backend.db import get_connection, DB_FILE, init_database
from backend.article_structure import unwrap_text


class StorageError(Exception):
    pass


class CacheManager:
    def __init__(self, default_ttl_seconds: int = 300):
        self.default_ttl = default_ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            entry = self._cache[key]
            if time.time() < entry["expires_at"]:
                self.hits += 1
                return entry["data"]
            else:
                del self._cache[key]
        self.misses += 1
        return None

    def set(self, key: str, data: Any, ttl_seconds: Optional[int] = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        self._cache[key] = {
            "data": data,
            "expires_at": time.time() + ttl
        }

    def invalidate(self, key_prefix: Optional[str] = None) -> int:
        if not key_prefix:
            count = len(self._cache)
            self._cache.clear()
            return count
        keys_to_remove = [k for k in self._cache if k.startswith(key_prefix)]
        for k in keys_to_remove:
            del self._cache[k]
        return len(keys_to_remove)

    def stats(self) -> Dict[str, Any]:
        total = self.hits + self.misses
        hit_ratio = (self.hits / total) if total > 0 else 0.0
        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": total,
            "hit_ratio": round(hit_ratio, 4),
            "cached_entries": len(self._cache)
        }


# Load tiers and aliases dynamically from config/ (zero hardcoded act IDs)
CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
TIERS_PATH = os.path.join(CONFIG_DIR, "tiers.yaml")
ALIASES_PATH = os.path.join(CONFIG_DIR, "act_aliases.json")

POPULAR_ACT_IDS = set()
POPULAR_ACT_NAMES = set()
COMMON_ALIASES = {}

def reload_tiers_and_aliases():
    global POPULAR_ACT_IDS, POPULAR_ACT_NAMES, COMMON_ALIASES
    import yaml
    if os.path.exists(TIERS_PATH):
        try:
            with open(TIERS_PATH, "r", encoding="utf-8") as f:
                t_cfg = yaml.safe_load(f) or {}
                POPULAR_ACT_IDS = set(t_cfg.get("tier_1", {}).get("acts", []))
        except Exception:
            pass
    if os.path.exists(ALIASES_PATH):
        try:
            with open(ALIASES_PATH, "r", encoding="utf-8") as f:
                COMMON_ALIASES = json.load(f)
                POPULAR_ACT_NAMES = set(COMMON_ALIASES.keys())
        except Exception:
            pass

reload_tiers_and_aliases()

def calculate_act_relevance(item: Dict[str, Any], query_str: str) -> int:
    name = item["name"]
    act_id = item["id"]
    category = item.get("category", "") or ""
    q = query_str.strip().lower()
    name_lower = name.lower()
    score = 0
    
    # 0. Alias match
    target_id = COMMON_ALIASES.get(query_str.strip())
    if target_id and act_id == target_id:
        score += 3000

    # 1. Exact title match
    if name_lower == q:
        score += 2500
    # 2. Prefix title match
    elif name_lower.startswith(q):
        score += 1000
    # 3. Contains title match & position weighting
    elif q in name_lower:
        pos = name_lower.find(q)
        score += 400 + max(0, 100 - pos * 5)
    elif q in category.lower():
        score += 50
    elif q in act_id.lower():
        score += 80

    # 4. Popular core statutes boost
    if act_id in POPULAR_ACT_IDS or name in POPULAR_ACT_NAMES:
        score += 600

    # 5. Statute hierarchy weighting (Statute vs Administrative Order/Rules)
    if name.endswith(("法", "律", "條例", "通則")):
        score += 200
    elif name.endswith(("辦法", "標準", "細則", "規程", "要點", "注意事項")):
        score -= 50

    # 6. Length penalty (Longer names are penalized so 42-char orders don't override 5-char core laws)
    score -= len(name) * 2

    return score

class LegalStorage:
    def __init__(self, acts_dir: Optional[str] = None, db_path: str = DB_FILE):
        self.acts_dir = acts_dir
        self.db_path = db_path
        self.cache = CacheManager()
        init_database(self.db_path)

    def load_all_acts(self):
        self.cache.invalidate()

    def add_act(self, data: Dict[str, Any]) -> Act:
        act_id = data.get("id", "").strip()
        act_name = data.get("name", "").strip()

        if not act_id:
            raise ValidationError("Act ID is required.")

        conn = get_connection(self.db_path)
        cur = conn.cursor()

        # Duplicate act ID check
        cur.execute("SELECT id FROM acts WHERE id = ?", (act_id,))
        if cur.fetchone():
            conn.close()
            raise StorageError(f"Duplicate act ID '{act_id}' is already registered.")

        # Duplicate act Name check
        cur.execute("SELECT id FROM acts WHERE name = ?", (act_name,))
        if cur.fetchone():
            conn.close()
            raise StorageError(f"Duplicate act name '{act_name}' is already registered.")

        # Validate with Model
        act = Act(**data)

        # Insert to SQLite
        cur.execute("""
            INSERT INTO acts (
                id, pcode, name, name_en, last_modified, category, 
                org_reform_notice, history_json, legislative_process_json, 
                chapters_json, attachments_json, is_enriched
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            act.id,
            data.get("pcode", act.id),
            act.name,
            act.name_en,
            act.last_modified,
            act.category,
            act.org_reform_notice,
            json.dumps(act.history, ensure_ascii=False),
            json.dumps(act.legislative_process, ensure_ascii=False),
            json.dumps(act.chapters, ensure_ascii=False),
            json.dumps([att.to_dict() for att in act.attachments], ensure_ascii=False),
            1
        ))

        for art in act.articles:
            cur.execute("""
                INSERT INTO articles (act_id, article_no, title, chapter, content)
                VALUES (?, ?, ?, ?, ?)
            """, (act.id, art.article_no, art.title, art.chapter, art.content))

            # Enrichments
            cur.execute("""
                INSERT INTO article_enrichments (
                    act_id, article_no, summary, reading_time, vernacular_qa_json,
                    elements_json, key_issues_json, legislative_reasons,
                    amendment_history_json, practical_insights_json, lawplayer_link,
                    related_articles_json, attachments_json, faqs_json,
                    comparison_table_json, legal_definition, flowchart_json, official_letters_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                act.id,
                art.article_no,
                art.summary,
                art.reading_time,
                json.dumps(art.vernacular_qa, ensure_ascii=False),
                json.dumps(art.elements, ensure_ascii=False),
                json.dumps(art.key_issues, ensure_ascii=False),
                art.legislative_reasons,
                json.dumps(art.amendment_history, ensure_ascii=False),
                json.dumps(art.practical_insights, ensure_ascii=False),
                art.lawplayer_link,
                json.dumps(art.related_articles, ensure_ascii=False),
                json.dumps([att.to_dict() for att in art.attachments], ensure_ascii=False),
                json.dumps(art.faqs, ensure_ascii=False),
                json.dumps(art.comparison_table, ensure_ascii=False),
                art.legal_definition,
                json.dumps(art.flowchart, ensure_ascii=False),
                json.dumps(art.official_letters, ensure_ascii=False)
            ))

            # FTS5 insert
            try:
                cur.execute("""
                    INSERT INTO articles_fts (act_id, article_no, title, content)
                    VALUES (?, ?, ?, ?)
                """, (act.id, art.article_no, art.title, art.content))
            except Exception:
                pass

        conn.commit()
        conn.close()
        self.cache.invalidate()
        return act

    def get_act(self, act_id: str) -> Optional[Act]:
        cache_key = f"act:{act_id}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT * FROM acts WHERE id = ? OR pcode = ? OR name = ?", (act_id, act_id, act_id))
        row = cur.fetchone()
        if not row:
            conn.close()
            return None

        # Fetch articles joined with enrichments
        cur.execute("""
            SELECT 
                a.act_id, a.article_no, a.title, a.chapter, a.content, a.title_source, a.label_raw,
                e.summary, e.reading_time, e.vernacular_qa_json, e.elements_json,
                e.key_issues_json, e.legislative_reasons, e.amendment_history_json,
                e.practical_insights_json, e.lawplayer_link, e.related_articles_json,
                e.attachments_json, e.faqs_json, e.comparison_table_json,
                e.legal_definition, e.flowchart_json, e.official_letters_json,
                e.source, e.source_url, e.fetched_at, e.article_hash,
                e.paywalled_counts_json
            FROM articles a
            LEFT JOIN article_enrichments e 
                ON a.act_id = e.act_id AND a.article_no = e.article_no
            WHERE a.act_id = ?
            ORDER BY a.rowid ASC
        """, (row["id"],))
        art_rows = cur.fetchall()

        # Query LIS article_reasons & article_comparison
        cur.execute("""
            SELECT article_no, version_date, action_type, reason, source, source_url, fetched_at,
                   date_label_raw, date_raw, article_no_at_the_time, source_mode
            FROM article_reasons
            WHERE act_id = ?
            ORDER BY version_date DESC
        """, (row["id"],))
        reasons_by_art = {}
        for r_row in cur.fetchall():
            art_no = r_row["article_no"]
            if art_no not in reasons_by_art:
                reasons_by_art[art_no] = []
            reasons_by_art[art_no].append({
                "version_date": r_row["version_date"],
                "action_type": r_row["action_type"],
                "reason": r_row["reason"],
                "source": r_row["source"],
                "source_url": r_row["source_url"],
                "fetched_at": r_row["fetched_at"],
                "date_label_raw": r_row["date_label_raw"] or "",
                "date_raw": r_row["date_raw"] or "",
                "article_no_at_the_time": r_row["article_no_at_the_time"] or "",
                "source_mode": r_row["source_mode"] or "fullpage"
            })

        cur.execute("""
            SELECT article_no, new_version_date, old_version_date, action_type,
                   new_content, old_content, reason, table_data, source, source_url, fetched_at,
                   date_label_raw, date_raw, article_no_at_the_time, source_mode,
                   col_headers_json, cells_json
            FROM article_comparison
            WHERE act_id = ?
            ORDER BY new_version_date DESC
        """, (row["id"],))
        comp_by_art = {}
        for c_row in cur.fetchall():
            art_no = c_row["article_no"]
            if art_no not in comp_by_art:
                comp_by_art[art_no] = []
            comp_by_art[art_no].append({
                "new_version_date": c_row["new_version_date"],
                "old_version_date": c_row["old_version_date"],
                "action_type": c_row["action_type"],
                "new_content": c_row["new_content"],
                "old_content": c_row["old_content"],
                "reason": c_row["reason"],
                "table_data": json.loads(c_row["table_data"] or "[]"),
                "col_headers": json.loads(c_row["col_headers_json"] or "[]"),
                "cells": json.loads(c_row["cells_json"] or "[]"),
                "source": c_row["source"],
                "source_url": c_row["source_url"],
                "fetched_at": c_row["fetched_at"],
                "date_label_raw": c_row["date_label_raw"] or "",
                "date_raw": c_row["date_raw"] or "",
                "article_no_at_the_time": c_row["article_no_at_the_time"] or "",
                "source_mode": c_row["source_mode"] or "fullpage"
            })

        conn.close()

        articles = []
        for a in art_rows:
            articles.append({
                "article_no": a["article_no"],
                "label_raw": a["label_raw"] if "label_raw" in a.keys() and a["label_raw"] else "",
                "title": a["title"] or "",
                "title_source": a["title_source"] if "title_source" in a.keys() else "",
                "chapter": a["chapter"] or "",
                "content": a["content"],
                "reading_time": a["reading_time"] or "",
                "summary": a["summary"] or "",
                "legislative_reasons": a["legislative_reasons"] or "",
                "vernacular_qa": json.loads(a["vernacular_qa_json"] or "[]"),
                "elements": json.loads(a["elements_json"] or "[]"),
                "key_issues": json.loads(a["key_issues_json"] or "[]"),
                "amendment_history": json.loads(a["amendment_history_json"] or "[]"),
                "practical_insights": json.loads(a["practical_insights_json"] or "[]"),
                "attachments": json.loads(a["attachments_json"] or "[]"),
                "lawplayer_link": a["lawplayer_link"] or "",
                "related_articles": json.loads(a["related_articles_json"] or "[]"),
                "faqs": json.loads(a["faqs_json"] or "[]"),
                "comparison_table": json.loads(a["comparison_table_json"] or "{}"),
                "legal_definition": a["legal_definition"] or "",
                "flowchart": json.loads(a["flowchart_json"] or "{}"),
                "official_letters": json.loads(a["official_letters_json"] or "[]"),
                "source": a["source"] if "source" in a.keys() and a["source"] else "",
                "source_url": a["source_url"] if "source_url" in a.keys() and a["source_url"] else "",
                "fetched_at": a["fetched_at"] if "fetched_at" in a.keys() and a["fetched_at"] else "",
                "article_hash": a["article_hash"] if "article_hash" in a.keys() and a["article_hash"] else "",
                "paywalled_counts": json.loads(a["paywalled_counts_json"] or "{}") if "paywalled_counts_json" in a.keys() and a["paywalled_counts_json"] else {},
                "lis_reasons": reasons_by_art.get(a["article_no"], []),
                "lis_comparison": comp_by_art.get(a["article_no"], []),
                "status": a["status"] if "status" in a.keys() and a["status"] else "active",
                "stale": a["stale"] if "stale" in a.keys() and a["stale"] else 0
            })

        act_data = {
            "id": row["id"],
            "pcode": row["pcode"] if "pcode" in row.keys() and row["pcode"] else "",
            "name": row["name"],
            "name_en": row["name_en"] or "",
            "last_modified": row["last_modified"] or "",
            "category": row["category"] or "",
            "org_reform_notice": row["org_reform_notice"] or "",
            "history": json.loads(row["history_json"] or "[]"),
            "legislative_process": json.loads(row["legislative_process_json"] or "[]"),
            "chapters": json.loads(row["chapters_json"] or "[]"),
            "attachments": json.loads(row["attachments_json"] or "[]"),
            "status": row["status"] if "status" in row.keys() and row["status"] else "active",
            "effective_date": row["effective_date"] if "effective_date" in row.keys() and row["effective_date"] else "",
            "effective_note": row["effective_note"] if "effective_note" in row.keys() and row["effective_note"] else "",
            "abandon_note": row["abandon_note"] if "abandon_note" in row.keys() and row["abandon_note"] else "",
            "foreword": unwrap_text(row["foreword"]) if "foreword" in row.keys() and row["foreword"] else "",
            "sync_time": row["last_modified"] or "",
            "articles": articles
        }

        act = Act(**act_data)
        self.cache.set(cache_key, act)
        return act

    def list_acts(self, query: str = "") -> List[Dict[str, Any]]:
        q = (query or "").strip().lower()
        cache_key = f"acts:list:{q}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        conn = get_connection(self.db_path)
        cur = conn.cursor()
        if q:
            cur.execute("""
                SELECT id, name, name_en, last_modified, category 
                FROM acts 
                WHERE lower(name) LIKE ? OR lower(category) LIKE ? OR lower(id) LIKE ?
            """, (f"%{q}%", f"%{q}%", f"%{q}%"))
        else:
            cur.execute("SELECT id, name, name_en, last_modified, category FROM acts ORDER BY is_enriched DESC, name ASC")

        rows = cur.fetchall()
        conn.close()

        results = []
        for r in rows:
            item = {
                "id": r["id"],
                "name": r["name"],
                "name_en": r["name_en"] or "",
                "last_modified": r["last_modified"] or "",
                "category": r["category"] or ""
            }
            if q:
                item["_score"] = calculate_act_relevance(item, query)
            results.append(item)

        if q:
            # Sort by relevance score DESC, then shorter name ASC, then alphabetical name ASC
            results.sort(key=lambda x: (x["_score"], -len(x["name"]), x["name"]), reverse=True)
            for res in results:
                res.pop("_score", None)

        self.cache.set(cache_key, results)
        return results

    def get_article(self, act_id: str, article_no: str) -> Optional[Article]:
        act = self.get_act(act_id)
        if not act:
            return None
        return act.articles_map.get(str(article_no).strip())

    def get_article_revisions(self, act_id: str, article_no: str) -> List[Dict[str, Any]]:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT id, act_id, article_no, old_content, new_content, old_hash, new_hash,
                   change_type, detected_at, source_modified_date
            FROM article_revisions
            WHERE act_id = ? AND article_no = ?
            ORDER BY detected_at DESC
        """, (act_id, str(article_no).strip()))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def get_article_panel(self, act_id: str, article_no: str) -> Optional[Dict[str, Any]]:
        """
        Universal Article Panel (Prompt 4C):
        Returns fixed sections list with strict status:
        - present: Data available
        - source_has_none: Source queried, confirmed no data for this article
        - not_attempted: Source not yet queried
        - not_applicable: Source does not cover this category by nature (e.g. orders in LIS)
        """
        act = self.get_act(act_id)
        if not act:
            return None
        
        real_act_id = act.id
        art_no_str = str(article_no).strip()
        art = act.articles_map.get(art_no_str)
        
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        
        sections = []
        
        # 1. 官方條文 (全國法規資料庫 MOJ)
        if art:
            sections.append({
                "section_type": "official_text",
                "title": "官方條文",
                "source": "全國法規資料庫",
                "status": "present",
                "items": [{
                    "article_no": art.article_no,
                    "title": art.title or "",
                    "content": art.content,
                    "status": art.status
                }],
                "fetched_at": act.last_modified or ""
            })
        else:
            sections.append({
                "section_type": "official_text",
                "title": "官方條文",
                "source": "全國法規資料庫",
                "status": "source_has_none",
                "items": [],
                "fetched_at": act.last_modified or ""
            })

        # 2. 法規/條文沿革 (全國法規資料庫 MOJ)
        act_history = act.history or []
        sections.append({
            "section_type": "act_history",
            "title": "法規沿革",
            "source": "全國法規資料庫",
            "status": "present" if act_history else "source_has_none",
            "items": act_history,
            "fetched_at": act.last_modified or ""
        })

        # 3. 立法理由與修正條文對照表 (立法院法律系統 LIS)
        cat = (act.category or "").strip()
        is_order = ("命令" in cat) or ("行政規則" in cat)
        
        reason_rows = []
        comp_rows = []
        reasons_status = "not_attempted"
        comp_status = "not_attempted"
        
        if is_order:
            reasons_status = "not_applicable"
            comp_status = "not_applicable"
            sections.append({
                "section_type": "legislative_reasons",
                "title": "立法理由",
                "source": "立法院法律系統",
                "status": "not_applicable",
                "items": [],
                "fetched_at": ""
            })
            sections.append({
                "section_type": "amendment_comparison",
                "title": "修正條文對照表",
                "source": "立法院法律系統",
                "status": "not_applicable",
                "items": [],
                "fetched_at": ""
            })
        else:
            cur.execute("""
                SELECT reason, date_label_raw, date_raw, action_type, source_url, fetched_at
                FROM article_reasons
                WHERE act_id = ? AND article_no = ?
                ORDER BY version_date DESC, id DESC
            """, (real_act_id, art_no_str))
            reason_rows = [dict(r) for r in cur.fetchall()]

            cur.execute("""
                SELECT new_version_date, old_version_date, action_type, new_content, old_content,
                       reason, table_data, col_headers_json, cells_json, date_label_raw, date_raw,
                       source_url, fetched_at
                FROM article_comparison
                WHERE act_id = ? AND article_no = ?
                ORDER BY new_version_date DESC, id DESC
            """, (real_act_id, art_no_str))
            comp_rows = [dict(r) for r in cur.fetchall()]

            for cr in comp_rows:
                if cr.get("col_headers_json"):
                    try:
                        cr["col_headers"] = json.loads(cr["col_headers_json"])
                    except Exception:
                        cr["col_headers"] = []
                if cr.get("cells_json"):
                    try:
                        cr["cells"] = json.loads(cr["cells_json"])
                    except Exception:
                        cr["cells"] = []

            cur.execute("SELECT count(*) FROM law_legislative_history WHERE act_id = ?", (real_act_id,))
            c_hist = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM article_reasons WHERE act_id = ?", (real_act_id,))
            c_reas = cur.fetchone()[0]

            if reason_rows:
                reasons_status = "present"
            elif c_hist > 0 or c_reas > 0:
                reasons_status = "source_has_none"
            else:
                reasons_status = "not_attempted"

            if comp_rows:
                comp_status = "present"
            elif c_hist > 0 or c_reas > 0:
                comp_status = "source_has_none"
            else:
                comp_status = "not_attempted"

            sections.append({
                "section_type": "legislative_reasons",
                "title": "立法理由",
                "source": "立法院法律系統",
                "status": reasons_status,
                "items": reason_rows,
                "fetched_at": reason_rows[0].get("fetched_at") if reason_rows else ""
            })
            sections.append({
                "section_type": "amendment_comparison",
                "title": "修正條文對照表",
                "source": "立法院法律系統",
                "status": comp_status,
                "items": comp_rows,
                "fetched_at": comp_rows[0].get("fetched_at") if comp_rows else ""
            })

        # 4. 法律人公開內容 (法律人 LawPlayer)
        cur.execute("""
            SELECT summary, vernacular_qa_json, practical_insights_json, faqs_json,
                   official_letters_json, related_articles_json, source, source_url, fetched_at
            FROM article_enrichments
            WHERE act_id = ? AND article_no = ?
        """, (real_act_id, art_no_str))
        enr_row = cur.fetchone()
        lp_items = []
        if enr_row:
            d = dict(enr_row)
            has_content = bool(d.get("summary") or d.get("vernacular_qa_json") != "[]" or d.get("practical_insights_json") != "[]")
            lp_status = "present" if has_content else "source_has_none"
            lp_items = [d] if has_content else []
            sections.append({
                "section_type": "lawplayer_enrichments",
                "title": "法律人解析與函釋判決",
                "source": "法律人",
                "status": lp_status,
                "items": lp_items,
                "fetched_at": d.get("fetched_at") or ""
            })
        else:
            cur.execute("SELECT checked_at, not_found_at FROM law_map WHERE act_id = ? OR UPPER(pcode) = UPPER(?)", (real_act_id, act.pcode or ""))
            lm = cur.fetchone()
            if lm and (lm[0] or lm[1]):
                lp_status = "source_has_none"
            else:
                lp_status = "not_attempted"
            sections.append({
                "section_type": "lawplayer_enrichments",
                "title": "法律人解析與函釋判決",
                "source": "法律人",
                "status": lp_status,
                "items": [],
                "fetched_at": ""
            })

        # 5. 「文中提及本條」的解釋與裁判 (司法院裁判書系統 Prompt 5)
        sections.append({
            "section_type": "judicial_references",
            "title": "相關司法裁判與解釋",
            "source": "司法院裁判書系統",
            "status": "not_attempted",
            "items": [],
            "fetched_at": ""
        })

        # 6. 我的文獻 (使用者文獻庫 Prompt 5B)
        cur.execute("SELECT count(*) FROM literature_articles WHERE act_id = ? AND article_no = ?", (real_act_id, art_no_str))
        lit_count = cur.fetchone()[0]
        sections.append({
            "section_type": "user_literature",
            "title": "相關研究文獻",
            "source": "使用者文獻庫",
            "status": "present" if lit_count > 0 else "source_has_none",
            "items": [],
            "fetched_at": ""
        })

        conn.close()

        article_obj = {
            "status": "present" if art else "source_has_none",
            "article_no": art_no_str,
            "title": art.title if art else "",
            "content": art.content if art else "",
            "act_id": act.id,
            "act_name": act.name
        }

        return {
            "act_id": act.id,
            "article_no": art_no_str,
            "act_name": act.name,
            "act_status": act.status,
            "abandon_note": act.abandon_note,
            "effective_date": act.effective_date,
            "effective_note": act.effective_note,
            "category": act.category,
            "article": article_obj,
            "legislative_reasons": {
                "status": reasons_status,
                "items": reason_rows
            },
            "amendment_comparison": {
                "status": comp_status,
                "items": comp_rows
            },
            "lawplayer": {
                "status": lp_status,
                "items": lp_items
            },
            "sections": sections
        }

    def get_update_status(self) -> Dict[str, Any]:
        import yaml
        cfg_path = os.path.join(os.path.dirname(os.path.dirname(self.db_path)), "config", "sources.yaml")
        sources_meta = []
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
                sources_meta = cfg.get("sources", [])

        conn = get_connection(self.db_path)
        cur = conn.cursor()

        # Build status for each source
        sources_status = []
        for s in sources_meta:
            s_name = s.get("name")
            last_run = cur.execute("""
                SELECT run_id, started_at, finished_at, status, counts_json, error, dry_run
                FROM update_runs
                WHERE source = ?
                ORDER BY started_at DESC
                LIMIT 1
            """, (s_name,)).fetchone()

            last_success = cur.execute("""
                SELECT started_at
                FROM update_runs
                WHERE source = ? AND status = 'success'
                ORDER BY started_at DESC
                LIMIT 1
            """, (s_name,)).fetchone()

            # Consecutive failures
            recent_runs = cur.execute("""
                SELECT status FROM update_runs
                WHERE source = ?
                ORDER BY started_at DESC
                LIMIT 10
            """, (s_name,)).fetchall()
            fail_count = 0
            for r in recent_runs:
                if r[0] in ("failed", "fetch_failed", "canary_failed", "verify_failed_rolled_back", "exception_rolled_back"):
                    fail_count += 1
                else:
                    break

            sources_status.append({
                "name": s_name,
                "type": s.get("type", s_name),
                "description": s.get("description", ""),
                "location": s.get("location", "remote"),
                "check_frequency": s.get("check_frequency", "daily"),
                "enabled": s.get("enabled", True),
                "last_run": dict(last_run) if last_run else None,
                "last_success_at": last_success[0] if last_success else s.get("last_success_at", ""),
                "consecutive_failures": fail_count,
                "status": "normal" if fail_count == 0 else ("failed" if fail_count >= 5 else "warning")
            })

        # Recent changes split into "new_acts" (新增法規) and "modified_articles" (修正)
        raw_changes = [dict(r) for r in cur.execute("""
            SELECT uc.id, uc.run_id, uc.source, uc.act_id, a.name as act_name, a.last_modified as act_date_raw,
                   a.effective_date, a.effective_note, a.status as act_status, uc.article_no,
                   uc.change_type, uc.old_hash, uc.new_hash, uc.detail_json, uc.created_at
            FROM update_changes uc
            LEFT JOIN acts a ON a.id = uc.act_id
            ORDER BY uc.id DESC
            LIMIT 200
        """).fetchall()]

        new_acts = []
        modified_articles = []
        for rc in raw_changes:
            if rc.get("detail_json"):
                try:
                    rc["detail"] = json.loads(rc["detail_json"])
                except Exception:
                    rc["detail"] = {}
            if rc["change_type"] in ("onboard_act", "add_act"):
                new_acts.append(rc)
            else:
                modified_articles.append(rc)

        # Pending human review items
        pending_human_rows = [dict(r) for r in cur.execute("""
            SELECT id, type, old_pcode, new_pcode, law_name, reason, detected_at, status
            FROM pending_human
            WHERE status = 'pending'
            ORDER BY detected_at DESC
        """).fetchall()]

        # Pending items queue
        pending_lis_rows = [dict(r) for r in cur.execute("""
            SELECT id, act_id, article_no, detected_at, retry_count, status, last_checked_at
            FROM pending_lis
            ORDER BY detected_at DESC
        """).fetchall()]

        # Check LIS last sync age (> 14 days warning)
        lis_last_run = cur.execute("""
            SELECT finished_at FROM update_runs
            WHERE source = 'lis' AND status IN ('success', 'no_change')
            ORDER BY finished_at DESC LIMIT 1
        """).fetchone()
        lis_warning = ""
        lis_last_sync_time = lis_last_run[0] if lis_last_run and lis_last_run[0] else ""
        if lis_last_sync_time:
            try:
                t = datetime.datetime.fromisoformat(lis_last_sync_time.split(".")[0])
                diff_days = (datetime.datetime.now() - t).days
                if diff_days > 14:
                    lis_warning = f"LIS 本機同步已逾 {diff_days} 天未執行，請於本機執行同步管線並匯入至遠端。"
            except Exception:
                pass

        conn.close()
        return {
            "sources": sources_status,
            "new_acts": new_acts,
            "modified_articles": modified_articles,
            "recent_changes": raw_changes,
            "pending_human": pending_human_rows,
            "pending_lis": pending_lis_rows,
            "lis_last_sync_time": lis_last_sync_time,
            "lis_warning": lis_warning
        }

    def check_bookmarks(self, bookmarks: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        if not bookmarks:
            return []
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        notifications = []
        for bm in bookmarks:
            act_id = bm.get("act_id")
            art_no = str(bm.get("article_no", "")).strip()
            if not act_id or not art_no:
                continue
            row = cur.execute("""
                SELECT a.name as act_name, art.status, art.stale, art.content
                FROM articles art
                JOIN acts a ON a.id = art.act_id
                WHERE art.act_id = ? AND art.article_no = ?
            """, (act_id, art_no)).fetchone()
            if not row:
                continue
            act_name = row[0]
            status = row[1]
            stale = row[2]
            if status == "deleted":
                notifications.append({
                    "act_id": act_id,
                    "act_name": act_name,
                    "article_no": art_no,
                    "type": "deleted",
                    "message": f"您收藏的【{act_name} 第 {art_no} 條】已在最新修法中刪除。"
                })
            elif stale == 1:
                notifications.append({
                    "act_id": act_id,
                    "act_name": act_name,
                    "article_no": art_no,
                    "type": "modified",
                    "message": f"您收藏的【{act_name} 第 {art_no} 條】條文內容已修正更新。"
                })
        conn.close()
        return notifications

    def search_articles(self, act_id: str, query: str) -> List[Dict[str, Any]]:
        act = self.get_act(act_id)
        if not act:
            return []

        q = (query or "").strip().lower()
        if not q:
            return [art.to_dict() for art in act.articles]

        cache_key = f"search:{act_id}:{q}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        results = []
        for art in act.articles:
            match_no = q == art.article_no.lower() or f"第{q}條" in f"第{art.article_no}條"
            match_title = q in art.title.lower()
            match_content = q in art.content.lower()
            match_reasons = q in art.legislative_reasons.lower()
            match_summary = q in (art.summary or "").lower()
            match_insights = any(
                q in item.get("summary", "").lower() or q in item.get("ref", "").lower()
                for item in art.practical_insights
            )

            if match_no or match_title or match_content or match_reasons or match_summary or match_insights:
                results.append(art.to_dict())

        self.cache.set(cache_key, results)
        return results

    # ---------------- Literature Repository (二級維度：法條雙向綁定與文獻庫) ----------------
    def add_literature(self, data: Dict[str, Any]) -> str:
        lit = Literature(**data)
        conn = get_connection(self.db_path)
        cur = conn.cursor()

        # Enforce strict deduplication: 同標題 + 同作者 就不能重複儲存
        clean_title = (lit.title or "").strip()
        clean_author = (lit.author or "").strip()
        if clean_title and clean_author:
            cur.execute("""
                SELECT id FROM literature 
                WHERE TRIM(title) = ? AND TRIM(author) = ?
            """, (clean_title, clean_author))
            existing = cur.fetchone()
            if existing:
                existing_id = existing["id"]
                # Link cited articles to existing literature record without inserting duplicate
                for art in lit.cited_articles:
                    act_id = art.get("act_id", "").strip()
                    art_no = str(art.get("article_no", "")).strip()
                    if act_id and art_no:
                        cur.execute("""
                            INSERT OR IGNORE INTO literature_articles (literature_id, act_id, article_no)
                            VALUES (?, ?, ?)
                        """, (existing_id, act_id, art_no))
                conn.commit()
                conn.close()
                self.cache.invalidate("lit:")
                return existing_id

        cur.execute("""
            INSERT INTO literature (
                id, title, subtitle, author, author_affiliation,
                journal_name, pub_year, pub_date, volume, issue, pages,
                abstract, abstract_en, keywords, cited_judgments_json,
                references_json, related_literature_json, file_path,
                file_size_bytes, download_status, source_url, source_db
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title=excluded.title,
                subtitle=excluded.subtitle,
                author=excluded.author,
                author_affiliation=excluded.author_affiliation,
                journal_name=excluded.journal_name,
                pub_year=excluded.pub_year,
                pub_date=excluded.pub_date,
                volume=excluded.volume,
                issue=excluded.issue,
                pages=excluded.pages,
                abstract=excluded.abstract,
                abstract_en=excluded.abstract_en,
                keywords=excluded.keywords,
                cited_judgments_json=excluded.cited_judgments_json,
                references_json=excluded.references_json,
                related_literature_json=excluded.related_literature_json,
                file_path=excluded.file_path,
                file_size_bytes=excluded.file_size_bytes,
                download_status=excluded.download_status,
                source_url=excluded.source_url,
                source_db=excluded.source_db,
                updated_at=CURRENT_TIMESTAMP
        """, (
            lit.id,
            lit.title,
            lit.subtitle,
            lit.author,
            lit.author_affiliation,
            lit.journal_name,
            lit.pub_year,
            lit.pub_date,
            lit.volume,
            lit.issue,
            lit.pages,
            lit.abstract,
            lit.abstract_en,
            ",".join(lit.keywords) if isinstance(lit.keywords, list) else str(lit.keywords),
            json.dumps(lit.cited_judgments, ensure_ascii=False),
            json.dumps(lit.references, ensure_ascii=False),
            json.dumps(lit.related_literature, ensure_ascii=False),
            lit.file_path,
            lit.file_size_bytes,
            lit.download_status,
            lit.source_url,
            lit.source_db
        ))

        # Insert / update article dual-binding
        cur.execute("DELETE FROM literature_articles WHERE literature_id = ?", (lit.id,))
        for art in lit.cited_articles:
            act_id = art.get("act_id", "").strip()
            art_no = str(art.get("article_no", "")).strip()
            if act_id and art_no:
                cur.execute("""
                    INSERT OR IGNORE INTO literature_articles (literature_id, act_id, article_no)
                    VALUES (?, ?, ?)
                """, (lit.id, act_id, art_no))

        conn.commit()
        conn.close()
        self.cache.invalidate("lit:")
        return lit.id

    def find_literature_by_title_author(self, title: str, author: str) -> Optional[Dict[str, Any]]:
        """
        Pre-flight check: returns existing record if title and author match (ignoring whitespace).
        """
        clean_title = (title or "").strip()
        clean_author = (author or "").strip()
        if not clean_title:
            return None
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT id, title, author, file_size_bytes FROM literature WHERE TRIM(title) = ? AND TRIM(author) = ?", (clean_title, clean_author))
        row = cur.fetchone()
        conn.close()
        if row:
            return dict(row)
        return None

    def bind_article(self, lit_id: str, act_id: str, article_no: str):
        """
        Binds an existing literature item to an article without re-inserting or downloading.
        """
        if not lit_id or not act_id or not article_no:
            return
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            INSERT OR IGNORE INTO literature_articles (literature_id, act_id, article_no)
            VALUES (?, ?, ?)
        """, (lit_id, act_id, str(article_no).strip()))
        conn.commit()
        conn.close()

    def get_literature(self, lit_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT * FROM literature WHERE id = ?", (lit_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return None

        # Fetch linked articles
        cur.execute("""
            SELECT la.act_id, la.article_no, a.name as act_name
            FROM literature_articles la
            LEFT JOIN acts a ON la.act_id = a.id
            WHERE la.literature_id = ?
        """, (lit_id,))
        articles = [dict(r) for r in cur.fetchall()]
        conn.close()

        data = dict(row)
        data["keywords"] = [k.strip() for k in (data.get("keywords") or "").split(",") if k.strip()]
        data["cited_judgments"] = json.loads(data.get("cited_judgments_json") or "[]")
        data["references"] = json.loads(data.get("references_json") or "[]")
        data["related_literature"] = json.loads(data.get("related_literature_json") or "[]")
        data["cited_articles"] = articles
        data["file_size_kb"] = round((data.get("file_size_bytes") or 0) / 1024, 1)
        data["file_size_mb"] = round((data.get("file_size_bytes") or 0) / (1024 * 1024), 2)
        return data

    def update_literature_file(self, lit_id: str, file_path: str, file_size_bytes: int):
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            UPDATE literature
            SET file_path = ?, file_size_bytes = ?, download_status = 'downloaded', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (file_path, file_size_bytes, lit_id))
        conn.commit()
        conn.close()
        self.cache.invalidate("literature:")

    def list_literature(
        self,
        query: str = "",
        author: str = "",
        journal_name: str = "",
        year: Optional[int] = None,
        act_id: str = "",
        article_no: str = "",
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        conn = get_connection(self.db_path)
        cur = conn.cursor()

        where_clauses = []
        params: List[Any] = []

        if query:
            where_clauses.append("(l.title LIKE ? OR l.subtitle LIKE ? OR l.abstract LIKE ? OR l.keywords LIKE ? OR l.author LIKE ? OR l.journal_name LIKE ?)")
            q_param = f"%{query}%"
            params.extend([q_param, q_param, q_param, q_param, q_param, q_param])

        if author:
            where_clauses.append("l.author LIKE ?")
            params.append(f"%{author}%")

        if journal_name:
            where_clauses.append("l.journal_name LIKE ?")
            params.append(f"%{journal_name}%")

        if year:
            where_clauses.append("l.pub_year = ?")
            params.append(year)

        join_clause = ""
        if act_id:
            join_clause = "JOIN literature_articles la ON l.id = la.literature_id"
            where_clauses.append("la.act_id = ?")
            params.append(act_id)
            if article_no:
                where_clauses.append("la.article_no = ?")
                params.append(str(article_no).strip())

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        # Count total
        cur.execute(f"SELECT COUNT(DISTINCT l.id) FROM literature l {join_clause} {where_sql}", tuple(params))
        total_items = cur.fetchone()[0]

        offset = max(0, (page - 1) * page_size)
        cur.execute(f"""
            SELECT DISTINCT l.id, l.title, l.subtitle, l.author, l.author_affiliation,
                   l.journal_name, l.pub_year, l.pub_date, l.volume, l.issue, l.pages,
                   l.file_path, l.file_size_bytes, l.download_status, l.source_db
            FROM literature l
            {join_clause}
            {where_sql}
            ORDER BY l.pub_year DESC, l.pub_date DESC, l.created_at DESC
            LIMIT ? OFFSET ?
        """, tuple(params + [page_size, offset]))
        rows = cur.fetchall()
        conn.close()

        items = []
        for r in rows:
            d = dict(r)
            d["file_size_kb"] = round((d.get("file_size_bytes") or 0) / 1024, 1)
            d["file_size_mb"] = round((d.get("file_size_bytes") or 0) / (1024 * 1024), 2)
            items.append(d)

        total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 1
        return {
            "items": items,
            "total_items": total_items,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }

    def get_literature_for_article(self, act_id: str, article_no: str, limit: int = 20) -> List[Dict[str, Any]]:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT l.id, l.title, l.subtitle, l.author, l.author_affiliation,
                   l.journal_name, l.pub_year, l.pub_date, l.volume, l.issue, l.pages,
                   l.abstract, l.file_path, l.file_size_bytes, l.download_status, l.source_db
            FROM literature l
            JOIN literature_articles la ON l.id = la.literature_id
            WHERE la.act_id = ? AND la.article_no = ?
            ORDER BY l.pub_year DESC, l.pub_date DESC
            LIMIT ?
        """, (act_id, str(article_no).strip(), limit))
        rows = cur.fetchall()
        conn.close()

        res = []
        for r in rows:
            d = dict(r)
            d["file_size_kb"] = round((d.get("file_size_bytes") or 0) / 1024, 1)
            d["file_size_mb"] = round((d.get("file_size_bytes") or 0) / (1024 * 1024), 2)
            res.append(d)
        return res

    def get_literature_stats(self) -> Dict[str, Any]:
        """
        Calculates storage, count, and size distribution metrics for downloaded literature.
        """
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*), COALESCE(SUM(file_size_bytes), 0) FROM literature")
        total_count, total_bytes = cur.fetchone()

        cur.execute("SELECT COUNT(*), COALESCE(SUM(file_size_bytes), 0) FROM literature WHERE download_status = 'downloaded'")
        downloaded_count, downloaded_bytes = cur.fetchone()

        # Distribution by year (from newest to oldest)
        cur.execute("""
            SELECT pub_year, COUNT(*), COALESCE(SUM(file_size_bytes), 0)
            FROM literature
            WHERE pub_year IS NOT NULL
            GROUP BY pub_year
            ORDER BY pub_year DESC
        """)
        year_dist = [
            {"year": r[0], "count": r[1], "bytes": r[2], "mb": round(r[2] / (1024 * 1024), 2)}
            for r in cur.fetchall()
        ]
        conn.close()

        avg_bytes = (downloaded_bytes / downloaded_count) if downloaded_count > 0 else 0

        return {
            "total_articles": total_count,
            "downloaded_articles": downloaded_count,
            "total_size_bytes": total_bytes,
            "downloaded_size_bytes": downloaded_bytes,
            "downloaded_size_mb": round(downloaded_bytes / (1024 * 1024), 2),
            "downloaded_size_gb": round(downloaded_bytes / (1024 * 1024 * 1024), 3),
            "average_file_size_kb": round(avg_bytes / 1024, 1),
            "average_file_size_mb": round(avg_bytes / (1024 * 1024), 2),
            "year_distribution": year_dist
        }


    def clear_all_literature(self) -> int:
        """
        Clears all literature records and dual bindings from database.
        """
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM literature")
        total = cur.fetchone()[0]
        cur.execute("DELETE FROM literature_articles")
        cur.execute("DELETE FROM literature")
        conn.commit()
        conn.close()
        self.cache.invalidate("literature:")
        return total


# Global singleton instance for shared usage
storage = LegalStorage()

