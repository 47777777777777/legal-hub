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


POPULAR_ACT_IDS = {
    "criminal_code", "civil_code", "constitution", 
    "criminal_procedure_code", "civil_procedure_code", 
    "labor_standards_act", "admin_procedure_act", 
    "traffic_act", "company_act"
}

POPULAR_ACT_NAMES = {
    "中華民國刑法", "民法", "中華民國憲法",
    "刑事訴訟法", "民事訴訟法", "勞動基準法",
    "行政程序法", "道路交通管理處罰條例", "公司法"
}

COMMON_ALIASES = {
    "刑法": "criminal_code",
    "民法": "civil_code",
    "憲法": "constitution",
    "刑訴": "criminal_procedure_code",
    "民訴": "civil_procedure_code",
    "勞基法": "labor_standards_act",
    "行政程序": "admin_procedure_act",
    "行程序": "admin_procedure_act",
    "公司法": "company_act",
    "交罰條例": "traffic_act",
    "道交條例": "traffic_act",
}

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
                a.act_id, a.article_no, a.title, a.chapter, a.content, a.title_source,
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
        conn.close()

        articles = []
        for a in art_rows:
            articles.append({
                "article_no": a["article_no"],
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
                "paywalled_counts": json.loads(a["paywalled_counts_json"] or "{}") if "paywalled_counts_json" in a.keys() and a["paywalled_counts_json"] else {}
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

