"""
Syncs official ChOrder.json (10,453 Taiwan Administrative Orders and Regulations)
into Legal Hub SQLite database, without overwriting existing statutory enrichments.
"""
import os
import sys
import json
import sqlite3
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.db import get_connection, DB_FILE, init_database

DATA_DIR = os.path.join(BASE_DIR, "data")
CHORDER_PATH = os.path.join(DATA_DIR, "ChOrder.json")

def clean_article_no(raw_no: str) -> str:
    s = raw_no.replace("第", "").replace("條", "").strip()
    s = s.replace("之", "-").replace(" ", "")
    return s

def sync_orders(db_path: str = DB_FILE):
    if not os.path.exists(CHORDER_PATH):
        print(f"Error: {CHORDER_PATH} not found. Please download ChOrder.json first.")
        return

    print(f"Loading {CHORDER_PATH}...")
    start_time = time.time()
    with open(CHORDER_PATH, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    orders = data.get("Laws", [])
    print(f"Loaded {len(orders)} orders in {time.time() - start_time:.2f}s. Beginning ingestion into SQLite...")

    init_database(db_path)
    conn = get_connection(db_path)
    cur = conn.cursor()

    total_acts_inserted = 0
    total_articles_inserted = 0
    skipped_acts = 0

    batch_acts = []
    batch_articles = []
    batch_fts = []

    for idx, order in enumerate(orders, 1):
        name = order.get("LawName", "").strip()
        if not name:
            continue

        url = order.get("LawURL", "")
        pcode = url.split("=")[-1] if "=" in url else ""
        if not pcode:
            pcode = f"ORD_{abs(hash(name)) % 10000000}"

        act_id = pcode.lower()
        name_en = order.get("EngLawName", "").strip()
        category = order.get("LawCategory", "").strip().replace("＞", " > ").replace("／", " > ").replace("/", " > ")
        # Tag category clearly as 法規命令 / 行政規則
        if category and not category.startswith("法規命令"):
            category = f"法規命令 > {category}"
        elif not category:
            category = "法規命令"

        modified_date = order.get("LawModifiedDate", "").strip()
        if len(modified_date) == 8 and modified_date.isdigit():
            y = int(modified_date[:4]) - 1911
            m = modified_date[4:6]
            d = modified_date[6:8]
            modified_date = f"民國 {y} 年 {m} 月 {d} 日"

        histories_raw = order.get("LawHistories", "")
        histories = [h.strip() for h in histories_raw.split("\r\n") if h.strip()] if histories_raw else []

        raw_items = order.get("LawArticles", [])
        current_part = ""
        current_chapter = ""
        current_section = ""
        parsed_chapters = []

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
                chapter_str = " / ".join(parts) if parts else "本規程"

                batch_articles.append((act_id, art_no, "", chapter_str, content))
                batch_fts.append((act_id, art_no, "", content))
                total_articles_inserted += 1

        batch_acts.append((
            act_id,
            pcode,
            name,
            name_en,
            modified_date,
            category,
            json.dumps(histories, ensure_ascii=False),
            json.dumps(parsed_chapters, ensure_ascii=False),
            0
        ))
        total_acts_inserted += 1

        # Execute in batches of 250
        if len(batch_acts) >= 250:
            cur.executemany("""
                INSERT OR IGNORE INTO acts (
                    id, pcode, name, name_en, last_modified, category,
                    history_json, chapters_json, is_enriched
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch_acts)

            if batch_articles:
                cur.executemany("""
                    INSERT OR IGNORE INTO articles (act_id, article_no, title, chapter, content)
                    VALUES (?, ?, ?, ?, ?)
                """, batch_articles)

            if batch_fts:
                try:
                    cur.executemany("""
                        INSERT INTO articles_fts (act_id, article_no, title, content)
                        VALUES (?, ?, ?, ?)
                    """, batch_fts)
                except Exception:
                    pass

            conn.commit()
            batch_acts.clear()
            batch_articles.clear()
            batch_fts.clear()
            print(f"Ingested {idx}/{len(orders)} orders ({total_articles_inserted} articles)...")

    # Final batch
    if batch_acts:
        cur.executemany("""
            INSERT OR IGNORE INTO acts (
                id, pcode, name, name_en, last_modified, category,
                history_json, chapters_json, is_enriched
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, batch_acts)

        if batch_articles:
            cur.executemany("""
                INSERT OR IGNORE INTO articles (act_id, article_no, title, chapter, content)
                VALUES (?, ?, ?, ?, ?)
            """, batch_articles)

        if batch_fts:
            try:
                cur.executemany("""
                    INSERT INTO articles_fts (act_id, article_no, title, content)
                    VALUES (?, ?, ?, ?)
                """, batch_fts)
            except Exception:
                pass

        conn.commit()

    conn.close()
    elapsed = time.time() - start_time
    print(f"Done! Successfully processed {total_acts_inserted} orders and {total_articles_inserted} articles in {elapsed:.2f}s!")

if __name__ == "__main__":
    sync_orders()
