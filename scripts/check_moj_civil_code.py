import sys
import json
import re

sys.stdout.reconfigure(encoding='utf-8')

with open('data/ChLaw.json', 'r', encoding='utf-8-sig') as f:
    laws = json.load(f)['Laws']

for l in laws:
    url = l.get('LawURL', '')
    m = re.search(r'pcode=([A-Z0-9]+)', url, re.I)
    pcode = m.group(1).upper() if m else ''
    name = l.get('LawName', '')
    
    if pcode == 'B0000001' or name == '民法':
        articles = l.get('LawArticles', [])
        print(f"MOJ Civil Code: Name={name}, Pcode={pcode}, Raw Articles Count={len(articles)}")
        # Check article numbers
        distinct_nos = set()
        active_articles = 0
        deleted_articles = 0
        for a in articles:
            no = a.get('ArticleNo')
            content = a.get('ArticleContent', '')
            distinct_nos.add(no)
            if '（刪除）' in content or '刪除' == content.strip():
                deleted_articles += 1
            else:
                active_articles += 1
        print(f"Distinct ArticleNo: {len(distinct_nos)}, Active: {active_articles}, Deleted: {deleted_articles}")
        # Print max article number
        int_nos = []
        for no in distinct_nos:
            try:
                int_nos.append(int(no.split('-')[0]))
            except:
                pass
        print(f"Max Article Number: {max(int_nos) if int_nos else 'N/A'}")
        break

