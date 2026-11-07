import os
import re
import json

raw_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'raw', 'lawplayer', 'civil_procedure_code')
cpc_act_path = os.path.join(raw_dir, 'cpc_act.body.html')

with open(cpc_act_path, 'r', encoding='utf-8') as f:
    html = f.read()

from bs4 import BeautifulSoup
soup = BeautifulSoup(html, 'html.parser')

# Find article links
# Check how articles are listed
links = soup.find_all('a', href=re.compile(r'^/article/[a-f0-9]+'))
print(f"Total /article/ links in cpc_act: {len(links)}")

lp_articles = {}
for a in links:
    href = a.get('href')
    txt = a.get_text(" ", strip=True)
    # Check format: "第 1 條 普通審判籍－自然人" or "第 244 條 起訴之程式"
    m = re.search(r'第\s*(\d+(?:之\d+)?)\s*條(?:\s*(.*))?', txt)
    if m:
        no = m.group(1)
        sub_title = m.group(2).strip() if m.group(2) else ""
        # deduplicate or save
        if no not in lp_articles:
            lp_articles[no] = {
                "id": href.split('/')[-1],
                "url": f"https://lawplayer.com{href}",
                "title": sub_title
            }

print(f"Unique articles parsed from LawPlayer cpc_act: {len(lp_articles)}")
sample_keys = list(lp_articles.keys())[:15]
for k in sample_keys:
    print(f"  Art {k}: {lp_articles[k]}")

