import os
import sys
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')
from backend.ccu_crawler import CCUCrawler
from backend.storage import storage

c = CCUCrawler()
for fn in ['scripts/ntu_law_review.html', 'scripts/lawdata_sample.html', 'scripts/lawdata_search_result.html']:
    if not os.path.exists(fn): continue
    with open(fn, "rb") as f:
        raw = f.read()
    h = c.decode_html(raw)
    parts = re.split(r'<td\s+', h, flags=re.I)
    arts = []
    i = 0
    while i < len(parts):
        p = parts[i]
        if 'class=tdc2' in p or 'class="tdc2"' in p:
            title = c.clean_cell(p)
            if c.is_valid_article_title(title):
                arts.append(title)
        i += 1
    print(fn, "-> valid articles:", len(arts))
