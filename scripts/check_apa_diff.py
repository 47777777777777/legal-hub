import sys
import json
import sqlite3
import os

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHLAW_PATH = os.path.join(BASE_DIR, "data", "ChLaw.json")
DB_PATH = os.path.join(BASE_DIR, "data", "legal_hub.db")

# 1. Get MOJ APA articles
with open(CHLAW_PATH, 'r', encoding='utf-8-sig') as f:
    laws = json.load(f)['Laws']

moj_apa_articles = set()
for l in laws:
    if l.get('LawName') == '行政程序法':
        for a in l.get('LawArticles', []):
            if a.get('ArticleType') == 'A':
                # extract article_no: "第 1 條" -> "1", "第 174-1 條" -> "174-1"
                raw_no = a.get('ArticleNo', '')
                clean_no = raw_no.replace('第', '').replace('條', '').strip()
                moj_apa_articles.add(clean_no)
        break

print(f"MOJ APA Type 'A' articles count: {len(moj_apa_articles)}")

# 2. Get DB article_reasons for admin_procedure_act
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("SELECT DISTINCT article_no FROM article_reasons WHERE act_id='admin_procedure_act'")
db_reasons_articles = set(r[0] for r in cur.fetchall())
conn.close()

print(f"DB article_reasons distinct articles count: {len(db_reasons_articles)}")

# 3. Set difference
only_in_moj = moj_apa_articles - db_reasons_articles
only_in_db = db_reasons_articles - moj_apa_articles

print(f"\nArticles in MOJ but NOT in DB article_reasons: {only_in_moj}")
print(f"Articles in DB article_reasons but NOT in MOJ: {only_in_db}")

