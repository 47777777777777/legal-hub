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
    m = re.search(r'第\s*(\d+(?:之\d+)?)\s*條(?:\s*(.*))?', txt)
    if m:
        no = m.group(1)
        sub_title = m.group(2).strip() if m.group(2) else ""
        if no not in lp_articles:
            lp_articles[no] = {
                "id": href.split('/')[-1],
                "url": f"https://lawplayer.com{href}",
                "title": sub_title
            }

# Compare with MOJ civil_procedure_code in legal_hub.db
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

titles_count = sum(1 for no in lp_set if lp_articles[no]["title"])
no_title_list = [no for no in lp_set if not lp_articles[no]["title"]]

print(f"MOJ Articles: {len(moj_set)}")
print(f"LawPlayer Articles: {len(lp_set)}")
print(f"Intersection: {len(common)}")
print(f"MOJ only count: {len(moj_only)}")
print(f"MOJ only sample: {moj_only[:20]}")
print(f"LawPlayer only count: {len(lp_only)}")
print(f"LawPlayer only sample: {lp_only[:20]}")
print(f"LawPlayer articles with title: {titles_count}")
print(f"LawPlayer articles without title: {len(no_title_list)}")

# Check deleted articles in MOJ
deleted_moj = [no for no, data in moj_articles.items() if '（刪除）' in data['content'] or '（刪除）' in (data['title'] or '') or data['content'] == '（刪除）' or not data['content']]
print(f"MOJ articles marked deleted or empty: {len(deleted_moj)}")

# Are the moj_only mostly deleted articles?
deleted_in_moj_only = set(moj_only).intersection(set(deleted_moj))
print(f"MOJ only that are deleted in MOJ: {len(deleted_in_moj_only)} / {len(moj_only)}")

