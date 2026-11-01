"""
Migration & Cleansing Script for Legal Hub:
1. Applies idempotent schema migration (source columns for article_enrichments, title_source for articles).
2. Clears non-authentic mock enrichments from article_enrichments.
3. Re-generates data/acts/civil_code.json and data/acts/criminal_code.json strictly from MOJ ChLaw.json.
4. Synchronizes authentic articles and titles into legal_hub.db.
"""
import os
import sys
import json
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.db import get_connection, DB_FILE, init_database
from backend.sync_opendata import clean_article_no, KNOWN_SLUGS

def run():
    print(f"Target database: {DB_FILE}")
    
    # 1. Apply schema migration
    init_database(DB_FILE)
    conn = get_connection(DB_FILE)
    cur = conn.cursor()
    
    # 2. Check enrichments before cleanup
    cur.execute("SELECT count(*) FROM article_enrichments")
    count_before = cur.fetchone()[0]
    print(f"BEFORE: SELECT count(*) FROM article_enrichments -> {count_before} rows")
    
    # Check breakdown by act_id
    cur.execute("SELECT act_id, count(*) FROM article_enrichments GROUP BY act_id")
    breakdown = cur.fetchall()
    print("Breakdown before deletion:")
    for r in breakdown:
        print(f"  {r[0]}: {r[1]} rows")
        
    # Delete non-authentic mock enrichments (all 438 mock rows)
    cur.execute("DELETE FROM article_enrichments WHERE source != 'lawplayer' OR source IS NULL OR source = ''")
    deleted_rows = cur.rowcount
    conn.commit()
    
    cur.execute("SELECT count(*) FROM article_enrichments")
    count_after = cur.fetchone()[0]
    print(f"\nDELETED: {deleted_rows} non-authentic enrichment rows")
    print(f"AFTER: SELECT count(*) FROM article_enrichments -> {count_after} rows")
    
    # 3. Load authentic titles
    lp_titles_path = os.path.join(BASE_DIR, "data", "all_authentic_lp_titles.json")
    authentic_titles = {}
    if os.path.exists(lp_titles_path):
        with open(lp_titles_path, "r", encoding="utf-8") as f:
            authentic_titles = json.load(f)
        print(f"Loaded authentic LawPlayer titles for {len(authentic_titles)} acts.")
    
    # 4. Load MOJ ChLaw.json
    chlaw_path = os.path.join(BASE_DIR, "data", "ChLaw.json")
    if not os.path.exists(chlaw_path):
        raise FileNotFoundError(f"ChLaw.json not found at {chlaw_path}")
        
    print(f"Reading official MOJ data from {chlaw_path}...")
    with open(chlaw_path, "r", encoding="utf-8-sig") as f:
        chlaw_data = json.load(f)
        
    laws_by_name = {l.get("LawName"): l for l in chlaw_data.get("Laws", [])}
    
    # Targets to regenerate
    targets = [
        ("civil_code", "民法"),
        ("criminal_code", "中華民國刑法")
    ]
    
    acts_dir = os.path.join(BASE_DIR, "data", "acts")
    os.makedirs(acts_dir, exist_ok=True)
    
    for act_id, law_name in targets:
        law = laws_by_name.get(law_name)
        if not law:
            print(f"WARNING: Law {law_name} not found in ChLaw.json!")
            continue
            
        url = law.get("LawURL", "")
        pcode = url.split("=")[-1] if "=" in url else ""
        name_en = law.get("EngLawName", "").strip()
        category = law.get("LawCategory", "").strip().replace("＞", " > ").replace("／", " > ").replace("/", " > ")
        modified_date = law.get("LawModifiedDate", "").strip()
        if len(modified_date) == 8 and modified_date.isdigit():
            y = int(modified_date[:4]) - 1911
            m = modified_date[4:6]
            d = modified_date[6:8]
            modified_date = f"民國 {y} 年 {m} 月 {d} 日"
            
        histories_raw = law.get("LawHistories", "")
        histories = [h.strip() for h in histories_raw.split("\r\n") if h.strip()] if histories_raw else []
        
        act_titles = authentic_titles.get(act_id, {})
        
        raw_items = law.get("LawArticles", [])
        current_part = ""
        current_chapter = ""
        current_section = ""
        parsed_chapters = []
        parsed_articles = []
        
        for item in raw_items:
            item_type = item.get("ArticleType", "")
            content = item.get("ArticleContent", "").strip()
            
            if item_type == "C":
                ch_title = content.replace("\r", " ").replace("\n", " ").strip()
                norm = " ".join([p.strip() for p in ch_title.split() if p.strip()])
                if "編" in norm:
                    current_part = norm
                    current_chapter = ""
                    current_section = ""
                elif "章" in norm:
                    current_chapter = norm
                    current_section = ""
                elif "節" in norm:
                    current_section = norm
                else:
                    current_chapter = norm
                    
                parsed_chapters.append({
                    "code": f"CH_{len(parsed_chapters) + 1}",
                    "title": norm
                })
            elif item_type == "A":
                raw_no = item.get("ArticleNo", "")
                art_no = clean_article_no(raw_no)
                if not art_no or not content:
                    continue
                    
                parts = [p for p in [current_part, current_chapter, current_section] if p]
                chapter_str = " / ".join(parts) if parts else "本法"
                title = act_titles.get(art_no, "")
                
                parsed_articles.append({
                    "article_no": art_no,
                    "title": title,
                    "chapter": chapter_str,
                    "content": content
                })
                
        # Write clean JSON
        out_json = {
            "id": act_id,
            "pcode": pcode,
            "name": law_name,
            "name_en": name_en,
            "last_modified": modified_date,
            "category": category,
            "history": histories,
            "chapters": parsed_chapters,
            "articles": parsed_articles
        }
        
        json_path = os.path.join(acts_dir, f"{act_id}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(out_json, f, ensure_ascii=False, indent=2)
        print(f"Regenerated {json_path} from MOJ ChLaw.json ({len(parsed_articles)} articles)")
        
        # Update SQLite acts table
        cur.execute("""
            INSERT OR REPLACE INTO acts (
                id, pcode, name, name_en, last_modified, category,
                history_json, chapters_json, attachments_json, is_enriched
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            act_id, pcode, law_name, name_en, modified_date, category,
            json.dumps(histories, ensure_ascii=False),
            json.dumps(parsed_chapters, ensure_ascii=False),
            json.dumps([], ensure_ascii=False),
            1
        ))
        
        # Update SQLite articles table
        for art in parsed_articles:
            title_src = "lawplayer" if art["title"] else ""
            cur.execute("""
                INSERT OR REPLACE INTO articles (act_id, article_no, title, chapter, content, title_source)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (act_id, art["article_no"], art["title"], art["chapter"], art["content"], title_src))
            
            # Update FTS5
            try:
                cur.execute("""
                    INSERT OR REPLACE INTO articles_fts (act_id, article_no, title, content)
                    VALUES (?, ?, ?, ?)
                """, (act_id, art["article_no"], art["title"], art["content"]))
            except Exception:
                pass
                
        print(f"Synced {act_id} ({law_name}) to database successfully.")
        
    conn.commit()
    conn.close()
    print("Database sync completed successfully!")

if __name__ == "__main__":
    run()
