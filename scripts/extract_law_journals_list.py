import re
import sys
import json

sys.stdout.reconfigure(encoding='utf-8')

with open('C:/Users/harry/.gemini/antigravity-ide/scratch/legal-hub/scripts/lawdata_periodicals.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

links = re.findall(r'<a[^>]*href=["\']?([^\s"\'>]+)["\']?[^>]*>([\s\S]*?)</a>', html, re.I)

legal_keywords = [
    '法', '律', '刑', '民', '商', '憲', '政', '裁判', '司法', '檢察', '軍法', 
    '論叢', '學報', '法粹', '法學', '律師', '專利', '智財', '智慧財產', '犯罪',
    '法治', '法制', '公平交易', '鑑識', '警察', 'Law', 'Review'
]

non_legal = ['醫事', '醫學', '護理', '體育', '照護', '測驗', '教育', '觀光', '遊憩', '華語', '病歷', '心理']

journals = []
seen = set()
for l, t in links:
    clean = re.sub(r'<[^>]+>', '', t).strip()
    if '^35^^^' in l and clean and not any(k in clean for k in ['查詢', '回首頁', '跳頁', '登出', '登入', '客服', 'more']):
        if clean not in seen:
            # Check if it matches legal keywords
            is_legal = any(k.lower() in clean.lower() for k in legal_keywords)
            # Check if it's explicitly non-legal (except medical law 醫事法 / 法律與生命科學)
            if '醫事法' in clean or '法律' in clean:
                is_legal = True
            elif any(nk in clean for nk in non_legal) and not any(k in clean for k in ['法', '律']):
                is_legal = False
                
            if is_legal:
                seen.add(clean)
                clean_path = l.lstrip('/')
                journals.append({"name": clean, "path": clean_path})

print(f"Total authentic law journals extracted: {len(journals)}")
for idx, j in enumerate(journals, 1):
    print(f"  {idx:02d}. {j['name']}")

with open('C:/Users/harry/.gemini/antigravity-ide/scratch/legal-hub/scripts/extracted_law_journals.json', 'w', encoding='utf-8') as f:
    json.dump(journals, f, ensure_ascii=False, indent=2)

