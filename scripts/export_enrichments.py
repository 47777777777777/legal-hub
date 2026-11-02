"""
scripts/export_enrichments.py

Exports authentic enriched articles from local SQLite DB to JSONL format.
Ensures strict provenance and sha256 article_hash are preserved for remote import verification.
"""

import os
import sys
import json
import sqlite3
import argparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "legal_hub.db")
DEFAULT_OUTPUT = os.path.join(BASE_DIR, "data", "enrichments_tier1.jsonl")


def export_enrichments(act_filter: str = None, output_path: str = DEFAULT_OUTPUT):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    query = """
        SELECT 
            act_id, article_no, summary, reading_time, vernacular_qa_json,
            elements_json, key_issues_json, legislative_reasons,
            amendment_history_json, practical_insights_json, lawplayer_link,
            related_articles_json, attachments_json, faqs_json,
            comparison_table_json, legal_definition, flowchart_json,
            official_letters_json, source, source_url, fetched_at,
            article_hash, paywalled_counts_json
        FROM article_enrichments
        WHERE source = 'lawplayer'
    """
    params = []
    if act_filter:
        query += " AND (act_id = ? OR act_id IN (SELECT id FROM acts WHERE pcode = ?))"
        params.extend([act_filter, act_filter])

    query += " ORDER BY act_id ASC, CAST(article_no AS INTEGER) ASC"

    cur.execute(query, params)
    rows = cur.fetchall()

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for r in rows:
            record = dict(r)
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    conn.close()
    print(f"Exported {len(rows)} enriched articles to {output_path}")
    return len(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export article enrichments to JSONL")
    parser.add_argument("--act", type=str, help="Specific act_id or pcode")
    parser.add_argument("--out", type=str, default=DEFAULT_OUTPUT, help="Output JSONL path")
    args = parser.parse_args()

    export_enrichments(args.act, args.out)
