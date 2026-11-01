import os
import sqlite3
import json
import hashlib
from datetime import datetime, timezone

from backend.lawplayer.parser import parse_article_page, parse_act_page

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
raw_dir = os.path.join(BASE_DIR, 'data', 'raw', 'lawplayer', 'civil_procedure_code')
db_path = os.path.join(BASE_DIR, 'data', 'legal_hub.db')

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# 1. Update titles for civil_procedure_code in articles table
cpc_act_path = os.path.join(raw_dir, 'cpc_act.body.html')
with open(cpc_act_path, 'r', encoding='utf-8') as f:
    act_html = f.read()

act_articles = parse_act_page(act_html, source_url="https://lawplayer.com/act/6437d054e800e5f0b93015aa")
updated_titles_count = 0
for art_no, info in act_articles.items():
    if info["title"]:
        cur.execute("""
            UPDATE articles
            SET title = ?, title_source = ?
            WHERE act_id = 'civil_procedure_code' AND article_no = ?
        """, (info["title"], "lawplayer", art_no))
        if cur.rowcount > 0:
            updated_titles_count += 1

print(f"Updated {updated_titles_count} titles in articles table.")

# 2. Ingest detailed articles (Art 1, Art 244, Art 277) into article_enrichments
sample_files = {
    '1': ('cpc_art_1.body.html', 'https://lawplayer.com/article/6438cf48e800e5f0b932894f'),
    '244': ('cpc_art_244.body.html', 'https://lawplayer.com/article/6438cf6fe800e5f0b9328b7a'),
    '277': ('cpc_art_277.body.html', 'https://lawplayer.com/article/6438cf79e800e5f0b9328bfe')
}

now_iso = datetime.now(timezone.utc).isoformat()
enriched_count = 0

for art_no, (fname, s_url) in sample_files.items():
    fpath = os.path.join(raw_dir, fname)
    if not os.path.exists(fpath):
        continue
    with open(fpath, 'r', encoding='utf-8') as f:
        html = f.read()
    
    parsed = parse_article_page(html, source_url=s_url)
    
    # Get article content from DB to compute content hash
    cur.execute("SELECT content FROM articles WHERE act_id = 'civil_procedure_code' AND article_no = ?", (art_no,))
    row = cur.fetchone()
    content_hash = ""
    if row and row[0]:
        content_hash = hashlib.sha256(row[0].encode('utf-8')).hexdigest()
    
    # Store deep_reading in practical_insights_json if present
    practical_insights = []
    if parsed["deep_reading"]:
        practical_insights.append({
            "type": "深度解讀",
            "content": parsed["deep_reading"]
        })
    if parsed["judgments"]:
        for j in parsed["judgments"]:
            practical_insights.append({
                "type": "相關判決/判例",
                "court": j["court"],
                "ref": j["ref"],
                "url": j["url"]
            })

    # Insert or replace into article_enrichments
    cur.execute("""
        INSERT INTO article_enrichments (
            act_id, article_no, summary, vernacular_qa_json,
            practical_insights_json, amendment_history_json,
            official_letters_json, source, source_url, fetched_at, article_hash
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(act_id, article_no) DO UPDATE SET
            summary = excluded.summary,
            vernacular_qa_json = excluded.vernacular_qa_json,
            practical_insights_json = excluded.practical_insights_json,
            amendment_history_json = excluded.amendment_history_json,
            official_letters_json = excluded.official_letters_json,
            source = excluded.source,
            source_url = excluded.source_url,
            fetched_at = excluded.fetched_at,
            article_hash = excluded.article_hash
    """, (
        'civil_procedure_code',
        art_no,
        parsed["summary"],
        json.dumps(parsed["vernacular_qa"], ensure_ascii=False),
        json.dumps(practical_insights, ensure_ascii=False),
        json.dumps(parsed["revisions"], ensure_ascii=False),
        json.dumps(parsed["interpretations"], ensure_ascii=False),
        'lawplayer',
        s_url,
        now_iso,
        content_hash
    ))
    enriched_count += 1
    print(f"Enriched Civil Procedure Code Art {art_no}: {len(parsed['interpretations'])} interpretations, {len(parsed['judgments'])} judgments")

conn.commit()
conn.close()
print("Ingestion complete.")
