"""
Populates full legal corpus index and seed statutes into SQLite database
with exact LawPlayer fields from screenshots.
"""
import os
import sys
import json
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.db import get_connection, DB_FILE, init_database

ACTS_DIR = os.path.join(BASE_DIR, "data", "acts")

ADDITIONAL_STATUTES = []


def populate():
    init_database(DB_FILE)
    conn = get_connection(DB_FILE)
    cur = conn.cursor()

    cur.execute("DELETE FROM attachments")
    cur.execute("DELETE FROM article_enrichments")
    cur.execute("DELETE FROM articles")
    cur.execute("DELETE FROM acts")
    try:
        cur.execute("DELETE FROM articles_fts")
    except Exception:
        pass

    # 1. Load files from data/acts/*.json
    for fname in os.listdir(ACTS_DIR):
        if fname.endswith(".json"):
            fpath = os.path.join(ACTS_DIR, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
                insert_act_data(cur, data, is_enriched=1)

    # 2. Insert additional seed statutes
    for act_data in ADDITIONAL_STATUTES:
        insert_act_data(cur, act_data, is_enriched=1)

    conn.commit()
    conn.close()
    print("Database populated with complete LawPlayer schema!")


def insert_act_data(cur, data: dict, is_enriched: int = 1):
    act_id = data.get("id")
    name = data.get("name")
    if not act_id or not name:
        return

    cur.execute("""
        INSERT OR REPLACE INTO acts (
            id, pcode, name, name_en, last_modified, category, 
            org_reform_notice, history_json, legislative_process_json, 
            chapters_json, attachments_json, is_enriched
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        act_id,
        data.get("pcode", act_id),
        name,
        data.get("name_en", ""),
        data.get("last_modified", ""),
        data.get("category", ""),
        data.get("org_reform_notice", ""),
        json.dumps(data.get("history", []), ensure_ascii=False),
        json.dumps(data.get("legislative_process", []), ensure_ascii=False),
        json.dumps(data.get("chapters", []), ensure_ascii=False),
        json.dumps(data.get("attachments", []), ensure_ascii=False),
        is_enriched
    ))

    # Insert attachments
    for att in data.get("attachments", []):
        cur.execute("""
            INSERT OR REPLACE INTO attachments (id, act_id, article_no, title, file_type, url, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            att.get("id", f"att_{abs(hash(att.get('url', '')))}"),
            act_id,
            att.get("related_article"),
            att.get("title", ""),
            att.get("file_type", "PDF"),
            att.get("url", ""),
            att.get("description", "")
        ))

    # Insert articles
    for art in data.get("articles", []):
        art_no = str(art.get("article_no")).strip()
        cur.execute("""
            INSERT OR REPLACE INTO articles (act_id, article_no, title, chapter, content)
            VALUES (?, ?, ?, ?, ?)
        """, (
            act_id,
            art_no,
            art.get("title", ""),
            art.get("chapter", ""),
            art.get("content", "")
        ))

        try:
            cur.execute("""
                INSERT INTO articles_fts (act_id, article_no, title, content)
                VALUES (?, ?, ?, ?)
            """, (act_id, art_no, art.get("title", ""), art.get("content", "")))
        except Exception:
            pass

        # Enrichments: store rich LawPlayer payload
        cur.execute("""
            INSERT OR REPLACE INTO article_enrichments (
                act_id, article_no, summary, reading_time, vernacular_qa_json,
                elements_json, key_issues_json, legislative_reasons,
                amendment_history_json, practical_insights_json, lawplayer_link,
                related_articles_json, attachments_json, faqs_json,
                comparison_table_json, legal_definition, flowchart_json, official_letters_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            act_id,
            art_no,
            art.get("summary", ""),
            art.get("reading_time", "3 分鐘"),
            json.dumps(art.get("vernacular_qa", []), ensure_ascii=False),
            json.dumps(art.get("elements", []), ensure_ascii=False),
            json.dumps(art.get("key_issues", []), ensure_ascii=False),
            art.get("legislative_reasons", ""),
            json.dumps(art.get("amendment_history", []), ensure_ascii=False),
            json.dumps(art.get("practical_insights", []), ensure_ascii=False),
            art.get("lawplayer_link", f"https://lawplayer.com/act/#article_{art_no}"),
            json.dumps(art.get("related_articles", []), ensure_ascii=False),
            json.dumps(art.get("attachments", []), ensure_ascii=False),
            json.dumps(art.get("faqs", []), ensure_ascii=False),
            json.dumps(art.get("comparison_table", {}), ensure_ascii=False),
            art.get("legal_definition", ""),
            json.dumps(art.get("flowchart", {}), ensure_ascii=False),
            json.dumps(art.get("official_letters", []), ensure_ascii=False)
        ))


if __name__ == "__main__":
    populate()
