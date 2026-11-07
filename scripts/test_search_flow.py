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
}

def search_lawdata(kw: str):
    print(f"\n================ Searching LawData for: {kw} ================")
    # Step 1: Query form action
    post_data = {
        '_TTS_ACTION': '2',
        '_TTS_CONTROL': '59^1869995081^20',
        '_TTS.EXITWAY': '/disk1/lawkm/ttswebx.ini',
        '_TTS.EXITMARK': '',
        '_TTS.EXITLEVEL': '9',
        '_TTS.INI': 'lawkm',
        'TOPTERM': kw,
        '_IMG_查詢.x': '15',
        '_IMG_查詢.y': '15',
        'SYN_EASYSEARCH_CHECK': '1',
        'SYN_EASYSEARCH': 'on'
    }
    action_url = 'https://www-lawdata-com-tw.autorpa.lib.ccu.edu.tw:8443/anglekmc/lawkm?@@-1_830916349'
    encoded_data = urllib.parse.urlencode(post_data, encoding='big5', errors='ignore').encode('latin1')
    req = urllib.request.Request(action_url, data=encoded_data, headers=headers)
    
    with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
        html = resp.read().decode('utf-8', errors='replace')
        
    # Find periodical link
    # Look for: href="lawkm?@59^...^30^^^" or similar
    match = re.search(r'href=[\'"]?([^\s\'">]*\^30\^\^\^[^\s\'">]*)[\'"]?', html)
    if not match:
        print("Could not find Periodicals link in search result categories")
        return []
    
    periodical_path = match.group(1)
    if not periodical_path.startswith('/'):
        periodical_path = '/anglekmc/' + periodical_path
    periodical_url = 'https://www-lawdata-com-tw.autorpa.lib.ccu.edu.tw:8443' + periodical_path
    print(f"Periodical URL: {periodical_url}")
    
    # Step 2: Fetch periodicals list
    req2 = urllib.request.Request(periodical_url, headers=headers)
    with urllib.request.urlopen(req2, context=ctx, timeout=15) as resp2:
        raw2 = resp2.read()
        html2 = raw2.decode('utf-8', errors='replace')
        
    # Parse articles
    articles = []
    parts = re.split(r'<td\s+', html2, flags=re.I)
    i = 0
    while i < len(parts):
        p = parts[i]
        if 'class=tdc2' in p or 'class="tdc2"' in p:
            # Title & Link
            title_text = re.sub(r'<[^>]+>', '', p).strip()
            link_m = re.search(r'href=[\'"]?([^\s\'">]+)', p)
            link = link_m.group(1) if link_m else ""
            
            # Next is tdc3 (Journal)
            journal = ""
            if i + 1 < len(parts) and 'tdc3' in parts[i+1]:
                journal = re.sub(r'<[^>]+>', '', parts[i+1]).strip()
            
            # Next is tdc4 (Author)
            author = ""
            if i + 2 < len(parts) and 'tdc4' in parts[i+2]:
                author = re.sub(r'<[^>]+>', '', parts[i+2]).strip()
                
            # Next is tdc5 (Pub date)
            pub_date = ""
            if i + 3 < len(parts) and 'tdc5' in parts[i+3]:
                pub_date = re.sub(r'<[^>]+>', '', parts[i+3]).strip()
                
            if title_text:
                articles.append({
                    "title": title_text,
                    "journal": journal,
                    "author": author,
                    "pub_date": pub_date,
                    "link": link
                })
        i += 1
        
    print(f"Found {len(articles)} real articles for query '{kw}':")
    for a in articles[:10]:
        print(f"  📖 [{a['pub_date']}] 《{a['title']}》 - {a['author']} ({a['journal']})")
    return articles

if __name__ == '__main__':
    search_lawdata('罪刑法定')
    search_lawdata('林山田')

