"""
Full Open Data Sync & Ingestion Engine for Taiwan Ministry of Justice Statutes.
Synchronizes complete official ChLaw.json into Legal Hub SQLite database.
"""
import os
import sys
import io
import json
import zipfile
import sqlite3
import urllib.request
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.db import get_connection, DB_FILE, init_database

DATA_DIR = os.path.join(BASE_DIR, "data")
CHLAW_PATH = os.path.join(DATA_DIR, "ChLaw.json")
OFFICIAL_LAWS_ZIP_URL = "https://law.moj.gov.tw/api/ch/law/json"

# Key statutory slugs mapping
KNOWN_SLUGS = {
    "中華民國刑法": "criminal_code",
    "民法": "civil_code",
    "中華民國憲法": "constitution",
    "勞動基準法": "labor_standards_act",
    "行政程序法": "admin_procedure_act",
    "道路交通管理處罰條例": "traffic_act",
    "公司法": "company_act",
    "刑事訴訟法": "criminal_procedure_code",
    "民事訴訟法": "civil_procedure_code",
    "個人資料保護法": "personal_data_protection_act",
    "著作權法": "copyright_act"
}

def clean_article_no(raw_no: str) -> str:
    s = raw_no.replace("第", "").replace("條", "").strip()
    s = s.replace("之", "-").replace(" ", "")
    return s

def ensure_chlaw_downloaded():
    if os.path.exists(CHLAW_PATH) and os.path.getsize(CHLAW_PATH) > 10000000:
        return CHLAW_PATH

    print("Downloading official open data from MOJ...")
    req = urllib.request.Request(
        OFFICIAL_LAWS_ZIP_URL,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) LegalHub/1.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        buf = io.BytesIO(resp.read())

    with zipfile.ZipFile(buf) as z:
        z.extract("ChLaw.json", DATA_DIR)

    return CHLAW_PATH

def sync_full_statutes(db_path: str = DB_FILE, limit_laws: int = None):
    chlaw_file = ensure_chlaw_downloaded()
    print(f"Loading {chlaw_file}...")
    with open(chlaw_file, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    laws = data.get("Laws", [])
    print(f"Total laws in official MOJ database: {len(laws)}")

    init_database(db_path)
    conn = get_connection(db_path)
    cur = conn.cursor()

    # Prioritize key laws first
    sorted_laws = sorted(
        laws,
        key=lambda l: 0 if l.get("LawName") in KNOWN_SLUGS else 1
    )

    if limit_laws:
        sorted_laws = sorted_laws[:limit_laws]

    total_inserted_articles = 0
    total_inserted_acts = 0

    for law in sorted_laws:
        name = law.get("LawName", "").strip()
        if not name:
            continue

        url = law.get("LawURL", "")
        pcode = url.split("=")[-1] if "=" in url else ""
        if not pcode:
            pcode = f"LAW_{abs(hash(name)) % 10000000}"

        act_id = KNOWN_SLUGS.get(name) or pcode.lower()
        name_en = law.get("EngLawName", "").strip()
        category = law.get("LawCategory", "").strip().replace("＞", " > ").replace("／", " > ").replace("/", " > ")
        modified_date = law.get("LawModifiedDate", "").strip()
        
        # Format modified date if YYYYMMDD
        if len(modified_date) == 8 and modified_date.isdigit():
            y = int(modified_date[:4]) - 1911
            m = modified_date[4:6]
            d = modified_date[6:8]
            modified_date = f"民國 {y} 年 {m} 月 {d} 日"

        histories_raw = law.get("LawHistories", "")
        histories = [h.strip() for h in histories_raw.split("\r\n") if h.strip()] if histories_raw else []

        # Load known titles and attachments from existing JSON file if present
        seed_titles = {}
        seed_attachments = []
        seed_path = os.path.join(DATA_DIR, "acts", f"{act_id}.json")
        if os.path.exists(seed_path):
            try:
                with open(seed_path, "r", encoding="utf-8") as sf:
                    seed_data = json.load(sf)
                    seed_attachments = seed_data.get("attachments", [])
                    for sart in seed_data.get("articles", []):
                        if sart.get("title"):
                            seed_titles[sart["article_no"]] = sart["title"]
            except Exception:
                pass

        # Parse articles and chapters hierarchy (編、章、節、款、目)
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
                # Clean multiple spaces: '第 一 編  總則' -> '第一編 總則'
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
                title = seed_titles.get(art_no, "")

                parsed_articles.append({
                    "article_no": art_no,
                    "title": title,
                    "chapter": chapter_str,
                    "content": content
                })

        # Insert Act
        cur.execute("""
            INSERT OR REPLACE INTO acts (
                id, pcode, name, name_en, last_modified, category,
                history_json, chapters_json, attachments_json, is_enriched
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            act_id,
            pcode,
            name,
            name_en,
            modified_date,
            category,
            json.dumps(histories, ensure_ascii=False),
            json.dumps(parsed_chapters, ensure_ascii=False),
            json.dumps(seed_attachments, ensure_ascii=False),
            1 if act_id in KNOWN_SLUGS else 0
        ))
        total_inserted_acts += 1

        # Insert attachments to attachments table
        for att in seed_attachments:
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

        # Insert Articles (Do not overwrite existing enrichments!)
        for art in parsed_articles:
            cur.execute("""
                INSERT OR REPLACE INTO articles (act_id, article_no, title, chapter, content)
                VALUES (?, ?, ?, ?, ?)
            """, (act_id, art["article_no"], art["title"], art["chapter"], art["content"]))

            # Insert into FTS
            try:
                cur.execute("""
                    INSERT INTO articles_fts (act_id, article_no, title, content)
                    VALUES (?, ?, ?, ?)
                """, (act_id, art["article_no"], art["title"], art["content"]))
            except Exception:
                pass

            total_inserted_articles += 1

    conn.commit()
    conn.close()

    print(f"Successfully synced {total_inserted_acts} acts and {total_inserted_articles} articles into {db_path}!")

if __name__ == "__main__":
    sync_full_statutes()
