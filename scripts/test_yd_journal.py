import urllib.request
import ssl
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')
ctx = ssl._create_unverified_context()
cookie = '_ga=GA1.1.1983743490.1793438764; _ga_WGHCEJZQV6=GS2.1.s1793489133$o2$g0$t1793489133$j60$l0$h0; flysheet-proxy=5963b762-9c6e-441b-a00a-c191e6adbdfd; lbkf=d0d5f061-0458-4ac6-ac8c-151522ede2da; lawbank=be5c468097bd41fea959b93e76e2cb3b-30; _ga_92YN8QGDF5=GS2.1.s1793493940$o2$g1$t1793493972$j28$l0$h0; _ga_BQBPZWYZE0=GS2.1.s1793493574$o5$g1$t1793495496$j58$l0$h0'

# Try fetching 月旦法學雜誌 (61A01001A100079739999621)
yd_law_journal_url = 'https://www-lawdata-com-tw.autorpa.lib.ccu.edu.tw:8443/anglekmc/lawkm?@59^1869995081^35^^^61A01001A100079739999621^@@767624107'

req = urllib.request.Request(yd_law_journal_url, headers={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36',
    'Cookie': cookie,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Referer': 'https://www-lawdata-com-tw.autorpa.lib.ccu.edu.tw:8443/anglekmc/lawkm?@59^1869995081^30^^^'
})

with urllib.request.urlopen(req, context=ctx, timeout=12) as r:
    html = r.read().decode('utf-8', errors='replace')
    print('Status:', r.status, 'Len:', len(html))
    print('Title:', re.findall(r'<title>(.*?)</title>', html, re.I))
    
    parts = re.split(r'<td\s+', html, flags=re.I)
    articles = []
    i = 0
    while i < len(parts):
        p = parts[i]
        if 'class=tdc2' in p or 'class="tdc2"' in p:
            title_text = re.sub(r'<[^>]+>', '', p).strip()
            journal = re.sub(r'<[^>]+>', '', parts[i+1]).strip() if i+1 < len(parts) else ""
            author = re.sub(r'<[^>]+>', '', parts[i+2]).strip() if i+2 < len(parts) else ""
            pub_date = re.sub(r'<[^>]+>', '', parts[i+3]).strip() if i+3 < len(parts) else ""
            articles.append((pub_date, title_text, author, journal))
        i += 1
    
    print(f"Extracted {len(articles)} articles from 月旦法學雜誌:")
    for pub_date, title, author, journal in articles:
        print(f"  [{pub_date}] 《{title}》 - {author} ({journal})")

