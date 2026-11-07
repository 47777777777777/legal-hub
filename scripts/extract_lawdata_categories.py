import re

with open('C:/Users/harry/.gemini/antigravity-ide/scratch/legal-hub/scripts/lawdata_search_result.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

matches = re.findall(r'<a[^>]*href=["\']?([^\s"\'>]+)["\']?[^>]*>([\s\S]*?)</a>', text)
for link, content in matches:
    clean = re.sub(r'<[^>]+>', '', content).strip()
    if any(k in clean for k in ['期刊', '論著', '文獻', '法學', '評論', '時報']) or '^30' in link or '^40' in link:
        print(f'{clean} -> {link}')

