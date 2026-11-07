import os
import sqlite3
import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
raw_dir = os.path.join(BASE_DIR, 'data', 'raw', 'lawplayer', 'civil_procedure_code')
cpc_act_path = os.path.join(raw_dir, 'cpc_act.body.html')

with open(cpc_act_path, 'r', encoding='utf-8') as f:
    html = f.read()

from bs4 import BeautifulSoup
soup = BeautifulSoup(html, 'html.parser')

links = soup.find_all('a', href=re.compile(r'^/article/[a-f0-9]+'))
lp_articles = {}
for a in links:
    href = a.get('href')
    txt = a.get_text(" ", strip=True)
    # Support hyphen: 第 31-1 條
    m = re.search(r'第\s*(\d+(?:[-－之]\d+)?)\s*條(?:\s*(.*))?', txt)
    if m:
        raw_no = m.group(1).replace('－', '-').replace('之', '-')
        sub_title = m.group(2).strip() if m.group(2) else ""
        if raw_no not in lp_articles:
            lp_articles[raw_no] = {
                "id": href.split('/')[-1],
                "url": f"https://lawplayer.com{href}",
                "title": sub_title
            }

db_path = os.path.join(BASE_DIR, 'data', 'legal_hub.db')
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("SELECT article_no, title, content FROM articles WHERE act_id = 'civil_procedure_code'")
moj_articles = {row[0]: {"title": row[1], "content": row[2]} for row in cur.fetchall()}
conn.close()

moj_set = set(moj_articles.keys())
lp_set = set(lp_articles.keys())

common = moj_set.intersection(lp_set)
moj_only = sorted(list(moj_set - lp_set), key=lambda x: [int(p) for p in re.findall(r'\d+', x)])
lp_only = sorted(list(lp_set - moj_set), key=lambda x: [int(p) for p in re.findall(r'\d+', x)])

print(f"MOJ Articles: {len(moj_set)}")
print(f"LawPlayer Articles: {len(lp_set)}")
print(f"Intersection: {len(common)}")
print(f"MOJ only count: {len(moj_only)}")
print(f"MOJ only: {moj_only}")
print(f"LawPlayer only count: {len(lp_only)}")

# Check what moj_only articles are
for no in moj_only:
    print(f"MOJ {no}: Title={moj_articles[no]['title']}, Content={repr(moj_articles[no]['content'][:40])}")

