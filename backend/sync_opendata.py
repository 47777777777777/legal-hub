"""
Open Data Ingestion Engine for Ministry of Justice Taiwan Statutes.
Downloads and synchronizes official Open Data (https://law.moj.gov.tw/api/ch/law/json)
into Legal Hub SQLite database.
"""
import os
import sys
import json
import urllib.request
import urllib.error

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.db import get_connection, DB_FILE, init_database

OFFICIAL_LAWS_API = "https://law.moj.gov.tw/api/ch/law/json"
OFFICIAL_ORDERS_API = "https://law.moj.gov.tw/api/ch/order/json"


def download_official_opendata(url: str, output_path: str) -> bool:
    print(f"Downloading official open data from {url}...")
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) LegalHub/1.0"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read()
            with open(output_path, "wb") as f:
                f.write(content)
        print(f"Successfully saved to {output_path} ({len(content)} bytes)")
        return True
    except Exception as e:
        print(f"Failed to download open data: {e}")
        return False


def import_raw_law_data(law_entry: dict, conn):
    cur = conn.cursor()
    pcode = law_entry.get("PCode") or law_entry.get("LawID") or ""
    name = law_entry.get("LawName", "").strip()
    category = law_entry.get("LawCategory", "")
    modified_date = law_entry.get("LawModifiedDate", "")
    act_id = f"moj_{pcode}" if pcode else f"law_{abs(hash(name))}"

    if not name:
        return

    cur.execute("""
        INSERT OR IGNORE INTO acts (id, pcode, name, last_modified, category)
        VALUES (?, ?, ?, ?, ?)
    """, (act_id, pcode, name, modified_date, category))

    articles = law_entry.get("LawArticles") or []
    for art in articles:
        art_no = art.get("ArticleNo") or str(art.get("ArticleIndex", ""))
        content = art.get("ArticleContent", "")
        if not art_no or not content:
            continue

        cur.execute("""
            INSERT OR IGNORE INTO articles (act_id, article_no, content)
            VALUES (?, ?, ?)
        """, (act_id, str(art_no).strip(), content.strip()))


if __name__ == "__main__":
    init_database()
    print("Open Data Ingestion Engine ready.")

