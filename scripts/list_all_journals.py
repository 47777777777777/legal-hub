import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('C:/Users/harry/.gemini/antigravity-ide/scratch/legal-hub/scripts/lawdata_periodicals.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

links = re.findall(r'<a[^>]*href=["\']?([^\s"\'>]+)["\']?[^>]*>([\s\S]*?)</a>', html, re.I)
journals = []
seen = set()
for l, t in links:
    clean = re.sub(r'<[^>]+>', '', t).strip()
    if '^35^^^' in l and clean and not any(k in clean for k in ['查詢', '回首頁', '跳頁', '登出', '登入', '客服']):
        if clean not in seen:
            seen.add(clean)
            journals.append((clean, l))

print(f"Total unique journals found in LawData: {len(journals)}")
for idx, (j, l) in enumerate(journals, 1):
    print(f"  {idx:02d}. {j} -> {l}")

