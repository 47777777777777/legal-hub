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

    # 1. Acts table (Supports both Slug 'criminal_code' and MOJ PCode 'C0000001')
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

    conn.commit()
    conn.close()


init_database()
