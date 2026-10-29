"""
SQLite Database Engine for Full Taiwan Statutes Corpus (30,000+ Acts).
Handles acts metadata, article index, LawPlayer enrichments, and search.
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

    # Acts table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS acts (
            id TEXT PRIMARY KEY,
            pcode TEXT,
            name TEXT NOT NULL,
            name_en TEXT,
            last_modified TEXT,
            category TEXT,
            org_reform_notice TEXT,
            history_json TEXT,
            legislative_process_json TEXT,
            chapters_json TEXT,
            attachments_json TEXT,
            is_enriched INTEGER DEFAULT 0
        )
    """)

    # Articles table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            act_id TEXT NOT NULL,
            article_no TEXT NOT NULL,
            title TEXT,
            chapter TEXT,
            content TEXT NOT NULL,
            reading_time TEXT DEFAULT '3 分鐘',
            summary TEXT,
            legislative_reasons TEXT,
            vernacular_qa_json TEXT,
            elements_json TEXT,
            key_issues_json TEXT,
            amendment_history_json TEXT,
            practical_insights_json TEXT,
            attachments_json TEXT,
            lawplayer_link TEXT,
            related_articles_json TEXT,
            UNIQUE(act_id, article_no),
            FOREIGN KEY (act_id) REFERENCES acts (id) ON DELETE CASCADE
        )
    """)

    # Indexes
    cur.execute("CREATE INDEX IF NOT EXISTS idx_acts_name ON acts(name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_acts_category ON acts(category)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_articles_lookup ON articles(act_id, article_no)")

    conn.commit()
    conn.close()


init_database()
