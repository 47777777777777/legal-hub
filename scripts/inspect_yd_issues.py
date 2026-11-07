import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('C:/Users/harry/.gemini/antigravity-ide/scratch/legal-hub/scripts/test_yd_journal.py', 'r') as f:
    pass

import urllib.request
import ssl

ctx = ssl._create_unverified_context()
cookie = '_ga=GA1.1.1983743490.1793438764; _ga_WGHCEJZQV6=GS2.1.s1793489133$o2$g0$t1793489133$j60$l0$h0; flysheet-proxy=5963b762-9c6e-441b-a00a-c191e6adbdfd; lbkf=d0d5f061-0458-4ac6-ac8c-151522ede2da; lawbank=be5c468097bd41fea959b93e76e2cb3b-30; _ga_92YN8QGDF5=GS2.1.s1793493940$o2$g1$t1793493972$j28$l0$h0; _ga_BQBPZWYZE0=GS2.1.s1793493574$o5$g1$t1793495496$j58$l0$h0'

yd_law_journal_url = 'https://www-lawdata-com-tw.autorpa.lib.ccu.edu.tw:8443/anglekmc/lawkm?@59^1869995081^35^^^61A01001A100079739999621^@@767624107'

req = urllib.request.Request(yd_law_journal_url, headers={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36',
    'Cookie': cookie,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Referer': 'https://www-lawdata-com-tw.autorpa.lib.ccu.edu.tw:8443/anglekmc/lawkm?@59^1869995081^30^^^'
})

with urllib.request.urlopen(req, context=ctx, timeout=12) as r:
    html = r.read().decode('utf-8', errors='replace')
    
links = re.findall(r'<a[^>]*href=["\']?([^\s"\'>]+)["\']?[^>]*>([\s\S]*?)</a>', html, re.I)
print(f"Total links on 月旦法學雜誌 page: {len(links)}")
for idx, (l, t) in enumerate(links):
    clean = re.sub(r'<[^>]+>', '', t).strip()
    if clean and any(k in clean for k in ['年', '期', '卷', '次頁', '下一頁', '上一頁']) or '^32^^^' in l or '^35^^^' in l:
        print(f"  [{clean}] -> {l}")

