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
    'Content-Type': 'application/x-www-form-urlencoded',
    'Referer': 'https://www-lawdata-com-tw.autorpa.lib.ccu.edu.tw:8443/anglekmc/ttswebx?@0:0:1:lawkm@@0.07765114904886061'
}

action_url = 'https://www-lawdata-com-tw.autorpa.lib.ccu.edu.tw:8443/anglekmc/lawkm?@@-1_830916349'

post_data = {
    '_TTS_ACTION': '2',
    '_TTS_CONTROL': '59^1869995081^20',
    '_TTS.EXITWAY': '/disk1/lawkm/ttswebx.ini',
    '_TTS.EXITMARK': '',
    '_TTS.EXITLEVEL': '9',
    '_TTS.INI': 'lawkm',
    'TOPTERM': '刑法',
    '_IMG_查詢.x': '15',
    '_IMG_查詢.y': '15',
    'SYN_EASYSEARCH_CHECK': '1',
    'SYN_EASYSEARCH': 'on'
}
encoded_data = urllib.parse.urlencode(post_data, encoding='big5', errors='ignore').encode('latin1')

req = urllib.request.Request(action_url, data=encoded_data, headers=headers)
with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
    search_bytes = resp.read()
    print('Search response status:', resp.status, 'len:', len(search_bytes))
    search_html = None
    for enc in ('big5', 'cp950', 'utf-8'):
        try:
            search_html = search_bytes.decode(enc)
            print(f'Decoded search results with {enc}!')
            break
        except Exception:
            pass
    if not search_html:
        search_html = search_bytes.decode('utf-8', errors='ignore')
        
    with open('scripts/lawdata_search_result.html', 'w', encoding='utf-8') as f:
        f.write(search_html)
        
    # Search for titles
    all_links = re.findall(r'<a[^>]*href=[\"\']?([^\s\"\'>]+)[\"\']?[^>]*>([\s\S]*?)</a>', search_html, re.I)
    print(f'Found {len(all_links)} total links in response:')
    real_count = 0
    for l, t in all_links:
        clean = re.sub(r'<[^>]+>', '', t).strip()
        if len(clean) > 4 and not any(k in clean for k in ['查詢', '上一頁', '下一頁', '回首頁', '跳頁', '登出', '登入', '說明', '客服', '品評家', '網路書店']):
            print(f'  📖 [{clean}] -> {l[:70]}')
            real_count += 1
            if real_count >= 15:
                break
    print(f'Total valid articles extracted: {real_count}')
