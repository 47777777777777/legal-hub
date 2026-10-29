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
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
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
            PRIMARY KEY (act_id, article_no),
            FOREIGN KEY (act_id) REFERENCES acts (id) ON DELETE CASCADE
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_articles_lookup ON articles(act_id, article_no)")

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
            PRIMARY KEY (act_id, article_no),
            FOREIGN KEY (act_id, article_no) REFERENCES articles(act_id, article_no) ON DELETE CASCADE
        )
    """)

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

    conn.commit()
    conn.close()


init_database()
