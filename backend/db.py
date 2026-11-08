"""
SQLite Database Engine for Full Taiwan Statutes Corpus (30,000+ Acts).
Includes FTS5 trigram tokenizer for Traditional Chinese full-text search,
dual-lookup index, and separated article_enrichments table.
"""
import sqlite3
import json
import os
from typing import Dict, List, Optional, Any

DB_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "legal_hub.db")


def get_connection(db_path: str = DB_FILE) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 5000")
    except Exception:
        pass
    return conn


def init_database(db_path: str = DB_FILE):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = get_connection(db_path)
    cur = conn.cursor()

    # 1. Acts table (Supports both Semantic Slug and MOJ PCode)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS acts (
            id TEXT PRIMARY KEY,
            pcode TEXT UNIQUE,
            name TEXT NOT NULL,
            name_en TEXT,
            category TEXT,
            last_modified TEXT,
            org_reform_notice TEXT,
            history_json TEXT DEFAULT '[]',
            legislative_process_json TEXT DEFAULT '[]',
            chapters_json TEXT DEFAULT '[]',
            attachments_json TEXT DEFAULT '[]',
            is_enriched INTEGER DEFAULT 0,
            is_standard INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_acts_name ON acts(name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_acts_pcode ON acts(pcode)")

    # 2. Articles table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            act_id TEXT NOT NULL,
            article_no TEXT NOT NULL,
            title TEXT,
            chapter TEXT,
            content TEXT NOT NULL,
            title_source TEXT DEFAULT '',
            label_raw TEXT DEFAULT '',
            PRIMARY KEY (act_id, article_no),
            FOREIGN KEY (act_id) REFERENCES acts (id) ON DELETE CASCADE
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_articles_lookup ON articles(act_id, article_no)")

    # Migration for articles table
    cur.execute("PRAGMA table_info(articles)")
    existing_art_cols = [c[1] for c in cur.fetchall()]
    if "title_source" not in existing_art_cols:
        try:
            cur.execute("ALTER TABLE articles ADD COLUMN title_source TEXT DEFAULT ''")
        except Exception:
            pass
    if "label_raw" not in existing_art_cols:
        try:
            cur.execute("ALTER TABLE articles ADD COLUMN label_raw TEXT DEFAULT ''")
        except Exception:
            pass

    # 3. Article Enrichments table (Preserved during open data sync)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS article_enrichments (
            act_id TEXT NOT NULL,
            article_no TEXT NOT NULL,
            summary TEXT,
            reading_time TEXT DEFAULT '3 分鐘',
            vernacular_qa_json TEXT DEFAULT '[]',
            elements_json TEXT DEFAULT '[]',
            key_issues_json TEXT DEFAULT '[]',
            legislative_reasons TEXT,
            amendment_history_json TEXT DEFAULT '[]',
            practical_insights_json TEXT DEFAULT '[]',
            lawplayer_link TEXT,
            related_articles_json TEXT DEFAULT '[]',
            attachments_json TEXT DEFAULT '[]',
            faqs_json TEXT DEFAULT '[]',
            comparison_table_json TEXT DEFAULT '{}',
            legal_definition TEXT DEFAULT '',
            flowchart_json TEXT DEFAULT '{}',
            official_letters_json TEXT DEFAULT '[]',
            source TEXT DEFAULT '',
            source_url TEXT DEFAULT '',
            fetched_at TEXT DEFAULT '',
            article_hash TEXT DEFAULT '',
            paywalled_counts_json TEXT DEFAULT '{}',
            PRIMARY KEY (act_id, article_no),
            FOREIGN KEY (act_id, article_no) REFERENCES articles(act_id, article_no) ON DELETE CASCADE
        )
    """)

    # Check and add columns if table already existed without new columns
    cur.execute("PRAGMA table_info(article_enrichments)")
    existing_cols = [c[1] for c in cur.fetchall()]
    new_cols = [
        ("faqs_json", "TEXT DEFAULT '[]'"),
        ("comparison_table_json", "TEXT DEFAULT '{}'"),
        ("legal_definition", "TEXT DEFAULT ''"),
        ("flowchart_json", "TEXT DEFAULT '{}'"),
        ("official_letters_json", "TEXT DEFAULT '[]'"),
        ("source", "TEXT DEFAULT ''"),
        ("source_url", "TEXT DEFAULT ''"),
        ("fetched_at", "TEXT DEFAULT ''"),
        ("article_hash", "TEXT DEFAULT ''"),
        ("paywalled_counts_json", "TEXT DEFAULT '{}'")
    ]
    for col_name, col_type in new_cols:
        if col_name not in existing_cols:
            try:
                cur.execute(f"ALTER TABLE article_enrichments ADD COLUMN {col_name} {col_type}")
            except Exception:
                pass

    # 4. Attachments table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS attachments (
            id TEXT PRIMARY KEY,
            act_id TEXT NOT NULL,
            article_no TEXT,
            title TEXT NOT NULL,
            file_type TEXT DEFAULT 'PDF',
            url TEXT NOT NULL,
            description TEXT,
            FOREIGN KEY (act_id) REFERENCES acts(id) ON DELETE CASCADE
        )
    """)

    # 5. Full-text search virtual table (FTS5 with trigram tokenizer for Traditional Chinese)
    try:
        cur.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
                act_id UNINDEXED,
                article_no UNINDEXED,
                title,
                content,
                tokenize='trigram'
            )
        """)
    except Exception as e:
        # Fallback if trigram is not available in specific environment
        print(f"FTS5 trigram notice: {e}")

    # 6. Literature table (Academic and professional legal literature)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS literature (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            subtitle TEXT DEFAULT '',
            author TEXT NOT NULL,
            author_affiliation TEXT DEFAULT '',
            journal_name TEXT NOT NULL,
            pub_year INTEGER,
            pub_date TEXT,
            volume TEXT DEFAULT '',
            issue TEXT DEFAULT '',
            pages TEXT DEFAULT '',
            abstract TEXT DEFAULT '',
            abstract_en TEXT DEFAULT '',
            keywords TEXT DEFAULT '',
            cited_judgments_json TEXT DEFAULT '[]',
            references_json TEXT DEFAULT '[]',
            related_literature_json TEXT DEFAULT '[]',
            file_path TEXT,
            file_size_bytes INTEGER DEFAULT 0,
            download_status TEXT DEFAULT 'pending',
            source_url TEXT DEFAULT '',
            source_db TEXT DEFAULT 'lawdata',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_lit_year ON literature(pub_year DESC, pub_date DESC)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_lit_author ON literature(author)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_lit_journal ON literature(journal_name)")

    # 7. Literature-Article dual-binding table (二級維度：法條關聯)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS literature_articles (
            literature_id TEXT NOT NULL,
            act_id TEXT NOT NULL,
            article_no TEXT NOT NULL,
            PRIMARY KEY (literature_id, act_id, article_no),
            FOREIGN KEY (literature_id) REFERENCES literature(id) ON DELETE CASCADE
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_lit_art_binding ON literature_articles(act_id, article_no)")

    # 8. Legislative reasons from LIS (立法院法律系統：立法理由)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS article_reasons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            act_id TEXT NOT NULL,
            article_no TEXT NOT NULL,
            version_date TEXT NOT NULL,
            action_type TEXT,
            reason TEXT NOT NULL,
            source TEXT DEFAULT '立法院法律系統',
            source_url TEXT,
            fetched_at TEXT,
            raw_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(act_id, article_no, version_date)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_reasons_art ON article_reasons(act_id, article_no)")

    # 9. Revision comparison table from LIS (立法院法律系統：修正條文對照表)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS article_comparison (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            act_id TEXT NOT NULL,
            article_no TEXT NOT NULL,
            new_version_date TEXT NOT NULL,
            old_version_date TEXT,
            action_type TEXT,
            new_content TEXT,
            old_content TEXT,
            reason TEXT,
            table_data TEXT,
            source TEXT DEFAULT '立法院法律系統',
            source_url TEXT,
            fetched_at TEXT,
            raw_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(act_id, article_no, new_version_date)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_comparison_art ON article_comparison(act_id, article_no)")

    # 10. Historical article versions from LIS (立法院法律系統：條文歷史版本)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS article_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            act_id TEXT NOT NULL,
            article_no TEXT NOT NULL,
            version_date TEXT NOT NULL,
            action_type TEXT,
            content TEXT NOT NULL,
            source TEXT DEFAULT '立法院法律系統',
            source_url TEXT,
            fetched_at TEXT,
            raw_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(act_id, article_no, version_date)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_versions_art ON article_versions(act_id, article_no)")

    # 11. Law legislative history from LIS (立法院法律系統：立法沿革)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS law_legislative_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            act_id TEXT NOT NULL,
            history_date TEXT NOT NULL,
            history_action TEXT NOT NULL,
            source TEXT DEFAULT '立法院法律系統',
            source_url TEXT,
            fetched_at TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(act_id, history_date)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_history_act ON law_legislative_history(act_id)")

    # 12. Idempotent column migrations for LIS tables (Prompt 3E)
    for tbl in ["article_reasons", "article_versions", "article_comparison"]:
        for col, col_type in [
            ("date_label_raw", "TEXT"),
            ("date_raw", "TEXT"),
            ("article_no_at_the_time", "TEXT"),
            ("source_mode", "TEXT DEFAULT 'fullpage'")
        ]:
            try:
                cur.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {col_type}")
            except sqlite3.OperationalError:
                pass

    for col, col_type in [
        ("col_headers_json", "TEXT"),
        ("cells_json", "TEXT")
    ]:
        try:
            cur.execute(f"ALTER TABLE article_comparison ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError:
            pass

    # 13. Update tracking & revision tables (Prompt 4)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS update_runs (
            run_id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            mode TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            status TEXT NOT NULL,
            counts_json TEXT DEFAULT '{}',
            error TEXT,
            dry_run INTEGER DEFAULT 1
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_update_runs_src ON update_runs(source, started_at)")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS update_changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            source TEXT NOT NULL,
            act_id TEXT NOT NULL,
            article_no TEXT,
            change_type TEXT NOT NULL,
            old_hash TEXT,
            new_hash TEXT,
            detail_json TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (run_id) REFERENCES update_runs(run_id)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_update_changes_run ON update_changes(run_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_update_changes_act ON update_changes(act_id, article_no)")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS article_revisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            act_id TEXT NOT NULL,
            article_no TEXT NOT NULL,
            old_content TEXT,
            new_content TEXT,
            old_hash TEXT,
            new_hash TEXT,
            change_type TEXT NOT NULL,
            detected_at TEXT NOT NULL,
            source_modified_date TEXT
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_revisions_act_art ON article_revisions(act_id, article_no)")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pending_lis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            act_id TEXT NOT NULL,
            article_no TEXT NOT NULL,
            detected_at TEXT NOT NULL,
            retry_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            last_checked_at TEXT,
            UNIQUE(act_id, article_no)
        )
    """)

    # 14. New act onboarding & human review tables (Prompt 4C)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS act_name_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            act_id TEXT NOT NULL,
            pcode TEXT NOT NULL,
            old_name TEXT NOT NULL,
            new_name TEXT NOT NULL,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_name_hist_act ON act_name_history(act_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_name_hist_old ON act_name_history(old_name)")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pending_human (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            old_pcode TEXT,
            new_pcode TEXT,
            law_name TEXT,
            reason TEXT,
            detected_at TEXT NOT NULL,
            status TEXT DEFAULT 'pending'
        )
    """)

    # 15. Law Map table for LawPlayer cross-reference (Prompt 3 & 4C)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS law_map (
            pcode TEXT PRIMARY KEY,
            act_id TEXT,
            lp_act_url TEXT,
            lp_name TEXT,
            matched_by TEXT,
            checked_at TEXT,
            not_found_at TEXT,
            next_retry_at TEXT,
            retry_count INTEGER DEFAULT 0
        )
    """)
    cur.execute("PRAGMA table_info(law_map)")
    lm_cols = [c[1] for c in cur.fetchall()]
    for col, ctype in [("not_found_at", "TEXT"), ("next_retry_at", "TEXT"), ("retry_count", "INTEGER DEFAULT 0")]:
        if col not in lm_cols:
            try:
                cur.execute(f"ALTER TABLE law_map ADD COLUMN {col} {ctype}")
            except sqlite3.OperationalError:
                pass

    # 16. Act Forewords table (Prompt 4D: 全國法規資料庫官方前言)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS act_forewords (
            act_id TEXT PRIMARY KEY,
            pcode TEXT NOT NULL,
            content TEXT NOT NULL,
            content_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_forewords_pcode ON act_forewords(pcode)")

    cur.execute("PRAGMA table_info(acts)")
    existing_act_cols = [c[1] for c in cur.fetchall()]
    if "foreword" not in existing_act_cols:
        try:
            cur.execute("ALTER TABLE acts ADD COLUMN foreword TEXT DEFAULT ''")
        except Exception:
            pass

    # Columns for articles (status, stale)
    cur.execute("PRAGMA table_info(articles)")
    art_cols = [c[1] for c in cur.fetchall()]
    for col, ctype in [("status", "TEXT DEFAULT 'active'"), ("stale", "INTEGER DEFAULT 0")]:
        if col not in art_cols:
            try:
                cur.execute(f"ALTER TABLE articles ADD COLUMN {col} {ctype}")
            except sqlite3.OperationalError:
                pass

    # 17. Text references (citations) table (Prompt 4E & 4G)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS text_refs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            act_id TEXT NOT NULL,
            article_no TEXT NOT NULL,
            ref_act_id TEXT,
            ref_article_no TEXT,
            ref_text TEXT NOT NULL,
            ref_type TEXT NOT NULL,
            start_pos INTEGER NOT NULL,
            end_pos INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_text_refs_source ON text_refs(act_id, article_no)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_text_refs_target ON text_refs(ref_act_id, ref_article_no)")

    # Columns for acts (status, effective_date, effective_note, abandon_note, effective_raw, effective_note_raw, first_seen_at, source_url, raw_path, content_hash, is_standard)
    cur.execute("PRAGMA table_info(acts)")
    act_cols = [c[1] for c in cur.fetchall()]
    for col, ctype in [
        ("status", "TEXT DEFAULT 'active'"),
        ("effective_date", "TEXT DEFAULT ''"),
        ("effective_note", "TEXT DEFAULT ''"),
        ("abandon_note", "TEXT DEFAULT ''"),
        ("effective_raw", "TEXT DEFAULT ''"),
        ("effective_note_raw", "TEXT DEFAULT ''"),
        ("first_seen_at", "TEXT"),
        ("source_url", "TEXT"),
        ("raw_path", "TEXT"),
        ("content_hash", "TEXT"),
        ("is_standard", "INTEGER DEFAULT 1")
    ]:
        if col not in act_cols:
            try:
                cur.execute(f"ALTER TABLE acts ADD COLUMN {col} {ctype}")
            except sqlite3.OperationalError:
                pass

    # Baseline migration: Align historically abolished acts with status='abolished' and abandon_note
    cur.execute("""
        UPDATE acts 
        SET status = 'abolished' 
        WHERE (category LIKE '%廢止法規%' OR (abandon_note IS NOT NULL AND abandon_note != ''))
          AND (status IS NULL OR status = 'active')
    """)

    # Baseline migration: Set is_standard for acts based on presence of label_raw in articles
    cur.execute("""
        UPDATE acts
        SET is_standard = 0
        WHERE id IN (
            SELECT act_id
            FROM articles
            GROUP BY act_id
            HAVING max(CASE WHEN label_raw IS NOT NULL AND trim(label_raw) != '' THEN 1 ELSE 0 END) = 0
        )
    """)

    # 18. Source attempts table (Prompt 4H & 4I)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS source_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            act_id TEXT NOT NULL,
            article_no TEXT NOT NULL,
            status TEXT NOT NULL,
            error_reason TEXT,
            duration_ms INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_source_attempts_act ON source_attempts(act_id, source)")

    conn.commit()
    conn.close()


init_database()
