import urllib.request
import urllib.parse
import ssl
import sys
import re
import random

sys.stdout.reconfigure(encoding='utf-8')

ctx = ssl._create_unverified_context()
cookie = '_ga=GA1.1.1983743490.1793438764; _ga_WGHCEJZQV6=GS2.1.s1793489133$o2$g0$t1793489133$j60$l0$h0; flysheet-proxy=5963b762-9c6e-441b-a00a-c191e6adbdfd; lbkf=d0d5f061-0458-4ac6-ac8c-151522ede2da; lawbank=be5c468097bd41fea959b93e76e2cb3b-30; _ga_92YN8QGDF5=GS2.1.s1793493940$o2$g1$t1793493972$j28$l0$h0; _ga_BQBPZWYZE0=GS2.1.s1793493574$o5$g1$t1793495496$j58$l0$h0'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36',
    'Cookie': cookie,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://www-lawdata-com-tw.autorpa.lib.ccu.edu.tw:8443/anglekmc/ttswebx?@lawkm'
}

def dynamic_search_lawdata(query: str):
    print(f"\n================ Dynamic LawData Search for: {query} ================")
    # Step 1: Get fresh form session
    rand_id = random.random()
    init_url = f'https://www-lawdata-com-tw.autorpa.lib.ccu.edu.tw:8443/anglekmc/ttswebx?@0:0:1:lawkm@@{rand_id}'
    req = urllib.request.Request(init_url, headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=12) as resp:
        init_html = resp.read().decode('utf-8', errors='replace')
        
    action_m = re.search(r'<form[^>]*name=TTSWEB[^>]*action=[\'"]?([^\s\'">]+)', init_html, re.I)
    if not action_m:
        action_m = re.search(r'<form[^>]*action=[\'"]?([^\s\'">]+)', init_html, re.I)
    if not action_m:
        print("Failed to find form action on LawData homepage!")
        return []
    
    action = action_m.group(1)
    if not action.startswith('http'):
        action_url = urllib.parse.urljoin('https://www-lawdata-com-tw.autorpa.lib.ccu.edu.tw:8443/anglekmc/', action)
    else:
        action_url = action
    print(f"Discovered dynamic action URL: {action_url}")
    
    # Extract hidden inputs
    post_data = {}
    for inp in re.findall(r'<input[^>]*>', init_html, re.I):
        name_m = re.search(r'name=[\'"]?([^\s\'">]+)', inp, re.I)
        val_m = re.search(r'value=[\'"]?([^\s\'">]*)', inp, re.I)
        if name_m and val_m:
            post_data[name_m.group(1)] = val_m.group(1)
            
    # Set search keyword and submit button
    post_data['TOPTERM'] = query
    post_data['_TTS_ACTION'] = '2'
    post_data['_IMG_查詢.x'] = '15'
    post_data['_IMG_查詢.y'] = '15'
    post_data['SYN_EASYSEARCH_CHECK'] = '1'
    post_data['SYN_EASYSEARCH'] = 'on'
    
    # Step 2: Submit search
    headers_post = headers.copy()
    headers_post['Content-Type'] = 'application/x-www-form-urlencoded'
    headers_post['Referer'] = init_url
    
    encoded_post = urllib.parse.urlencode(post_data, encoding='big5', errors='ignore').encode('latin1')
    req_post = urllib.request.Request(action_url, data=encoded_post, headers=headers_post)
    with urllib.request.urlopen(req_post, context=ctx, timeout=15) as resp_post:
        search_html = resp_post.read().decode('utf-8', errors='replace')
        
    # Step 3: Find Periodicals (期刊) link
    # Look for link with ^30^^^
    match = re.search(r'href=[\'"]?([^\s\'">]*\^30\^\^\^[^\s\'">]*)[\'"]?', search_html)
    if not match:
        print(f"No periodicals found or matched for query: {query}")
        return []
    
    p_path = match.group(1)
    p_url = urllib.parse.urljoin('https://www-lawdata-com-tw.autorpa.lib.ccu.edu.tw:8443/anglekmc/', p_path)
    print(f"Periodicals list URL: {p_url}")
    
    # Step 4: Fetch periodicals list
    headers_get = headers.copy()
    headers_get['Referer'] = action_url
    req_p = urllib.request.Request(p_url, headers=headers_get)
    with urllib.request.urlopen(req_p, context=ctx, timeout=15) as resp_p:
        p_html = resp_p.read().decode('utf-8', errors='replace')
        
    # Step 5: Parse articles
    articles = []
    parts = re.split(r'<td\s+', p_html, flags=re.I)
    i = 0
    while i < len(parts):
        p = parts[i]
        if 'class=tdc2' in p or 'class="tdc2"' in p:
            title_text = re.sub(r'<[^>]+>', '', p).strip()
            link_m = re.search(r'href=[\'"]?([^\s\'">]+)', p)
            link = urllib.parse.urljoin('https://www-lawdata-com-tw.autorpa.lib.ccu.edu.tw:8443/anglekmc/', link_m.group(1)) if link_m else ""
            
            journal = ""
            if i + 1 < len(parts) and ('tdc3' in parts[i+1]):
                journal = re.sub(r'<[^>]+>', '', parts[i+1]).strip()
            
            author = ""
            if i + 2 < len(parts) and ('tdc4' in parts[i+2]):
                author = re.sub(r'<[^>]+>', '', parts[i+2]).strip()
                
            pub_date = ""
            if i + 3 < len(parts) and ('tdc5' in parts[i+3]):
                pub_date = re.sub(r'<[^>]+>', '', parts[i+3]).strip()
                
            if title_text and len(title_text) > 3:
                articles.append({
                    "title": title_text,
                    "journal": journal,
                    "author": author,
                    "pub_date": pub_date,
                    "url": link,
                    "source": "月旦知識庫 (LawData)"
                })
        i += 1
        
    print(f"Successfully harvested {len(articles)} real articles for '{query}'!")
    for idx, a in enumerate(articles[:10], 1):
        print(f"  {idx}. [{a['pub_date']}] 《{a['title']}》")
        print(f"     作者: {a['author']} | 期刊: {a['journal']}")
        print(f"     URL: {a['url']}")
    return articles

if __name__ == '__main__':
    dynamic_search_lawdata('刑法')
    dynamic_search_lawdata('罪刑法定')

