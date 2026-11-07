import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('C:/Users/harry/.gemini/antigravity-ide/scratch/legal-hub/scripts/lawdata_periodicals.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

links = re.findall(r'<a[^>]*href=["\']?([^\s"\'>]+)["\']?[^>]*>([\s\S]*?)</a>', html, re.I)
for idx, (l, t) in enumerate(links):
    clean = re.sub(r'<[^>]+>', '', t).strip()
    if any(k in clean for k in ['月旦', '台灣法學', '裁判時報', '法學雜誌', '刑事法']):
        print(f'{idx}: [{clean}] -> {l}')

