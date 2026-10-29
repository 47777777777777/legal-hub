"""
Storage repository, duplicate validations, SQLite backing layer, and caching for Legal Hub.
Reconstructs domain models with full LawPlayer enrichments via LEFT JOIN.
"""
import os
import json
import time
import sqlite3
from typing import Dict, List, Optional, Any
from backend.models import Act, Article, Attachment, ValidationError
from backend.db import get_connection, DB_FILE, init_database


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
                a.act_id, a.article_no, a.title, a.chapter, a.content,
                e.summary, e.reading_time, e.vernacular_qa_json, e.elements_json,
                e.key_issues_json, e.legislative_reasons, e.amendment_history_json,
                e.practical_insights_json, e.lawplayer_link, e.related_articles_json,
                e.attachments_json, e.faqs_json, e.comparison_table_json,
                e.legal_definition, e.flowchart_json, e.official_letters_json
            FROM articles a
            LEFT JOIN article_enrichments e 
                ON a.act_id = e.act_id AND a.article_no = e.article_no
            WHERE a.act_id = ?
            ORDER BY a.rowid ASC
        """, (row["id"],))
        art_rows = cur.fetchall()
        conn.close()

        articles = []
        for a in art_rows:
            articles.append({
                "article_no": a["article_no"],
                "title": a["title"] or "",
                "chapter": a["chapter"] or "",
                "content": a["content"],
                "reading_time": a["reading_time"] or "3 分鐘",
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
                "official_letters": json.loads(a["official_letters_json"] or "[]")
            })

        act_data = {
            "id": row["id"],
            "name": row["name"],
            "name_en": row["name_en"] or "",
            "last_modified": row["last_modified"] or "",
            "category": row["category"] or "",
            "org_reform_notice": row["org_reform_notice"] or "",
            "history": json.loads(row["history_json"] or "[]"),
            "legislative_process": json.loads(row["legislative_process_json"] or "[]"),
            "chapters": json.loads(row["chapters_json"] or "[]"),
            "attachments": json.loads(row["attachments_json"] or "[]"),
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
                ORDER BY is_enriched DESC, name ASC
            """, (f"%{q}%", f"%{q}%", f"%{q}%"))
        else:
            cur.execute("SELECT id, name, name_en, last_modified, category FROM acts ORDER BY is_enriched DESC, name ASC")

        rows = cur.fetchall()
        conn.close()

        results = []
        for r in rows:
            results.append({
                "id": r["id"],
                "name": r["name"],
                "name_en": r["name_en"] or "",
                "last_modified": r["last_modified"] or "",
                "category": r["category"] or ""
            })

        self.cache.set(cache_key, results)
        return results

    def get_article(self, act_id: str, article_no: str) -> Optional[Article]:
        act = self.get_act(act_id)
        if not act:
            return None
        return act.articles_map.get(str(article_no).strip())

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
