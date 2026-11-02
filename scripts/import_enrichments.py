"""
scripts/import_enrichments.py

Imports enriched articles from JSONL into SQLite DB with strict SHA256 integrity check.
Runs on remote production server (161.33.166.144) or locally.
RULES:
- NEVER overwrite database with scp.
- Verify article content SHA256 matches article_hash before inserting.
- Mismatches are skipped and logged to reports/import_hash_mismatch.csv.
"""

import os
import sys
import json
import hashlib
import sqlite3
import argparse
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "legal_hub.db")
DEFAULT_INPUT = os.path.join(BASE_DIR, "data", "enrichments_tier1.jsonl")
MISMATCH_REPORT = os.path.join(BASE_DIR, "reports", "import_hash_mismatch.csv")


def import_enrichments(input_path: str = DEFAULT_INPUT, db_path: str = DB_PATH):
    if not os.path.exists(input_path):
        print(f"Error: JSONL file not found at {input_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Ensure paywalled_counts_json column exists
    cur.execute("PRAGMA table_info(article_enrichments)")
    existing_cols = {c[1] for c in cur.fetchall()}
    if "paywalled_counts_json" not in existing_cols:
        cur.execute("ALTER TABLE article_enrichments ADD COLUMN paywalled_counts_json TEXT DEFAULT '{}'")
        conn.commit()

    total_lines = 0
    imported_count = 0
    mismatch_count = 0
    missing_art_count = 0

    mismatches = []

    with open(input_path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            total_lines += 1
            rec = json.loads(line)

            act_id = rec["act_id"]
            art_no = rec["article_no"]
            expected_hash = rec.get("article_hash", "")

            # 1. Fetch current article from DB
            cur.execute("SELECT content FROM articles WHERE act_id = ? AND article_no = ?", (act_id, art_no))
            art_row = cur.fetchone()
            if not art_row:
                # Try finding by pcode
                cur.execute("""
                    SELECT a.act_id, a.content 
                    FROM articles a
                    JOIN acts ac ON a.act_id = ac.id
                    WHERE (ac.pcode = ? OR UPPER(ac.pcode) = UPPER(?)) AND a.article_no = ?
                """, (act_id, act_id, art_no))
                art_row = cur.fetchone()
                if art_row:
                    act_id = art_row["act_id"]

            if not art_row:
                missing_art_count += 1
                mismatches.append((act_id, art_no, expected_hash, "MISSING_IN_ARTICLES_TABLE"))
                continue

            # 2. Compute SHA256 hash of official content
            actual_content = art_row["content"] or ""
            actual_hash = hashlib.sha256(actual_content.encode("utf-8")).hexdigest()

            if actual_hash != expected_hash:
                mismatch_count += 1
                mismatches.append((act_id, art_no, expected_hash, actual_hash))
                continue

            # 3. UPSERT into article_enrichments
            cur.execute("""
                INSERT INTO article_enrichments (
                    act_id, article_no, summary, reading_time, vernacular_qa_json,
                    elements_json, key_issues_json, legislative_reasons,
                    amendment_history_json, practical_insights_json, lawplayer_link,
                    related_articles_json, attachments_json, faqs_json,
                    comparison_table_json, legal_definition, flowchart_json,
                    official_letters_json, source, source_url, fetched_at,
                    article_hash, paywalled_counts_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(act_id, article_no) DO UPDATE SET
                    summary = excluded.summary,
                    vernacular_qa_json = excluded.vernacular_qa_json,
                    practical_insights_json = excluded.practical_insights_json,
                    official_letters_json = excluded.official_letters_json,
                    amendment_history_json = excluded.amendment_history_json,
                    paywalled_counts_json = excluded.paywalled_counts_json,
                    lawplayer_link = excluded.lawplayer_link,
                    source = excluded.source,
                    source_url = excluded.source_url,
                    fetched_at = excluded.fetched_at,
                    article_hash = excluded.article_hash
            """, (
                act_id, art_no, rec.get("summary", ""), rec.get("reading_time", "3 分鐘"),
                rec.get("vernacular_qa_json", "[]"), rec.get("elements_json", "[]"),
                rec.get("key_issues_json", "[]"), rec.get("legislative_reasons", ""),
                rec.get("amendment_history_json", "[]"), rec.get("practical_insights_json", "[]"),
                rec.get("lawplayer_link", ""), rec.get("related_articles_json", "[]"),
                rec.get("attachments_json", "[]"), rec.get("faqs_json", "[]"),
                rec.get("comparison_table_json", "{}"), rec.get("legal_definition", ""),
                rec.get("flowchart_json", "{}"), rec.get("official_letters_json", "[]"),
                rec.get("source", "lawplayer"), rec.get("source_url", ""),
                rec.get("fetched_at", datetime.now().isoformat()),
                expected_hash, rec.get("paywalled_counts_json", "{}")
            ))
            imported_count += 1

    conn.commit()
    conn.close()

    # Log mismatches if any
    if mismatches:
        os.makedirs(os.path.dirname(MISMATCH_REPORT), exist_ok=True)
        with open(MISMATCH_REPORT, "w", encoding="utf-8") as f:
            f.write("act_id,article_no,expected_hash,actual_hash\n")
            for m in mismatches:
                f.write(f'"{m[0]}","{m[1]}","{m[2]}","{m[3]}"\n')

    print(f"=== Import Enrichments Report ===")
    print(f"Total lines read:    {total_lines}")
    print(f"Successfully upserted: {imported_count}")
    print(f"Hash mismatches (skipped): {mismatch_count}")
    print(f"Missing articles (skipped): {missing_art_count}")
    if mismatches:
        print(f"Details written to: {MISMATCH_REPORT}")
    return imported_count, mismatch_count, missing_art_count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import article enrichments from JSONL with hash verification")
    parser.add_argument("--in", dest="input_path", type=str, default=DEFAULT_INPUT, help="Input JSONL path")
    parser.add_argument("--db", dest="db_path", type=str, default=DB_PATH, help="Target SQLite database path")
    args = parser.parse_args()

    import_enrichments(args.input_path, args.db_path)
