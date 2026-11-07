import os
import json
import re
import sys
sys.path.insert(0, '.')
from bs4 import BeautifulSoup
from backend.lis.parser import parse_lis_article_no

def parse_comparisons_from_html(html, raw_path="", source_url=""):
    soup = BeautifulSoup(html, 'html.parser')
    comptbl = soup.find('div', id='comptable')
    if not comptbl:
        # fallback
        for tbl in soup.find_all('table'):
            txt = tbl.get_text(separator=' ', strip=True)
            if '版本法名稱' in txt and '版本條文' in txt:
                comptbl = tbl
                break
    if not comptbl:
        return []
        
    main_tbl = comptbl.find('table') if comptbl.name != 'table' else comptbl
    if not main_tbl:
        return []
        
    rows = []
    for tr in main_tbl.find_all('tr'):
        cells = [td.get_text(separator='\n', strip=True) for td in tr.find_all(['td', 'th'])]
        if cells and not (len(cells) == 1 and 'Copyright' in cells[0]):
            rows.append(cells)
            
    if len(rows) < 3:
        return []
        
    law_name = ""
    new_version_date = ""
    old_version_date = ""
    col_headers = []
    
    for r in rows:
        if len(r) >= 2 and r[0] == '版本法名稱':
            law_name = r[1].strip()
        elif len(r) >= 2 and r[0] == '版本條文':
            new_version_date = r[1].strip()
            if len(r) >= 3:
                old_version_date = r[2].strip()
            col_headers = r
            
    entries = []
    curr_art = None
    for r in rows:
        if not r:
            continue
        label = r[0]
        if '條' in label and any(k in label for k in ['修正', '增訂', '刪除']):
            m = re.search(r'(第[零一二三四五六七八九十百千萬\s]+(?:條之[零一二三四五六七八九十\s]+|條))\s*(?:\(([^\)]+)\))?', label)
            art_raw = m.group(1).replace(' ', '').strip() if m else label.strip()
            action_type = m.group(2) if m else ''
            curr_art = {
                'art_raw': art_raw,
                'action_type': action_type,
                'new_content': r[1].strip() if len(r) > 1 else '',
                'old_content': r[2].strip() if len(r) > 2 else '',
                'art_row': r,
                'reason': '',
                'reason_row': []
            }
            entries.append(curr_art)
        elif label == '理由' and curr_art:
            curr_art['reason'] = r[1].strip() if len(r) > 1 else ''
            curr_art['reason_row'] = r
            
    results = []
    for e in entries:
        art_no = parse_lis_article_no(e['art_raw'])
        specific_rows = [
            ['版本法名稱', law_name] + ([law_name] if old_version_date else []),
            col_headers,
            e['art_row']
        ]
        if e['reason_row']:
            specific_rows.append(e['reason_row'])
        results.append({
            'law_name': law_name,
            'article_no': art_no,
            'article_no_raw': e['art_raw'],
            'action_type': e['action_type'],
            'new_version_date': new_version_date,
            'old_version_date': old_version_date,
            'new_content': e['new_content'],
            'old_content': e['old_content'],
            'reason': e['reason'],
            'col_headers_json': json.dumps(col_headers, ensure_ascii=False),
            'cells_json': json.dumps(specific_rows, ensure_ascii=False),
            'date_label_raw': f"({new_version_date} {e['action_type']})" if (new_version_date or e['action_type']) else '',
            'date_raw': new_version_date,
            'article_no_at_the_time': e['art_raw'],
            'source_mode': 'singlepage',
            'source': '立法院法律系統',
            'source_url': source_url,
            'raw_path': raw_path
        })
    return results

if __name__ == '__main__':
    comp_dir = 'data/raw/lis/comparisons'
    total = 0
    for f in sorted(os.listdir(comp_dir)):
        if not f.startswith('comp_') or not f.endswith('.html'):
            continue
        content = open(os.path.join(comp_dir, f), 'r', encoding='utf-8').read()
        res = parse_comparisons_from_html(content, raw_path=f)
        print(f'{f}: {len(res)} comparisons')
        for r in res:
            print(f'   art_no={r["article_no"]} ({r["article_no_raw"]}), date={r["date_raw"]}, action={r["action_type"]}, cols={len(json.loads(r["col_headers_json"]))}')
        total += len(res)
    print(f'TOTAL comparison records parsed: {total}')
