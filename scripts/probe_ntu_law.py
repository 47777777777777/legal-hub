import urllib.request
import urllib.parse
import ssl
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

ctx = ssl._create_unverified_context()

cookie = '_ga=GA1.1.1983743490.1793438764; _ga_WGHCEJZQV6=GS2.1.s1793489133$o2$g0$t1793489133$j60$l0$h0; flysheet-proxy=5963b762-9c6e-441b-a00a-c191e6adbdfd; lbkf=d0d5f061-0458-4ac6-ac8c-151522ede2da; lawbank=be5c468097bd41fea959b93e76e2cb3b-30; _ga_92YN8QGDF5=GS2.1.s1793493940$o2$g1$t1793493972$j28$l0$h0; _ga_BQBPZWYZE0=GS2.1.s1793493574$o5$g1$t1793495496$j58$l0$h0'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36',
    'Cookie': cookie,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://www-lawdata-com-tw.autorpa.lib.ccu.edu.tw:8443/anglekmc/lawkm?@59^1869995081^30^^^'
}

# Let's test NTU Law Journal (國立臺灣大學法學論叢):
target_url = 'https://www-lawdata-com-tw.autorpa.lib.ccu.edu.tw:8443/anglekmc/lawkm?@59^1869995081^35^^^61A01015A520079734496999^@@915595231'

req = urllib.request.Request(target_url, headers=headers)
with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
    content_bytes = resp.read()
    html = None
    for enc in ('utf-8', 'cp950', 'big5'):
        try:
            html = content_bytes.decode(enc)
            print(f'Decoded with {enc}!')
            break
        except Exception:
            pass
    if not html:
        html = content_bytes.decode('utf-8', errors='ignore')

    with open('C:/Users/harry/.gemini/antigravity-ide/scratch/legal-hub/scripts/ntu_law_review.html', 'w', encoding='utf-8') as f:
        f.write(html)

    links = re.findall(r'<a[^>]*href=["\']?([^\s"\'>]+)["\']?[^>]*>([\s\S]*?)</a>', html, re.I)
    print(f'Total links: {len(links)}')
    for idx, (l, t) in enumerate(links[45:], 45):
        clean = re.sub(r'<[^>]+>', '', t).strip()
        if clean and not any(k in clean for k in ['查詢', '回首頁', '跳頁', '登出', '登入', '客服', '功能說明']):
            print(f'{idx}: [{clean}] -> {l}')
