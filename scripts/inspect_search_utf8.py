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
    'Referer': 'https://www-lawdata-com-tw.autorpa.lib.ccu.edu.tw:8443/anglekmc/ttswebx?@lawkm'
}

init_url = 'https://www-lawdata-com-tw.autorpa.lib.ccu.edu.tw:8443/anglekmc/ttswebx?@0:0:1:lawkm@@0.07765114904886061'
req = urllib.request.Request(init_url, headers=headers)
with urllib.request.urlopen(req, context=ctx, timeout=12) as resp:
    init_html = resp.read().decode('utf-8', errors='replace')

action_m = re.search(r'<form[^>]*action=[\'"]?([^\s\'">]+)', init_html, re.I)
action = action_m.group(1)
action_url = urllib.parse.urljoin('https://www-lawdata-com-tw.autorpa.lib.ccu.edu.tw:8443/anglekmc/', action)

post_data = {
    '_TTS_ACTION': '2',
    '_TTS_CONTROL': '60^889859532^20',
    'TOPTERM': '刑法',
    '_IMG_查詢.x': '15',
    '_IMG_查詢.y': '15',
    'SYN_EASYSEARCH_CHECK': '1',
    'SYN_EASYSEARCH': 'on'
}
encoded = urllib.parse.urlencode(post_data, encoding='utf-8').encode('ascii')
req_post = urllib.request.Request(action_url, data=encoded, headers={
    **headers,
    'Content-Type': 'application/x-www-form-urlencoded',
    'Referer': init_url
})

with urllib.request.urlopen(req_post, context=ctx, timeout=12) as r:
    html = r.read().decode('utf-8', errors='replace')
    print("Response URL:", r.url)
    print("Response Status:", r.status)
    print("Response HTML:\n", html[:1000])
    
links = re.findall(r'<a[^>]*href=["\']?([^\s"\'>]+)["\']?[^>]*>([\s\S]*?)</a>', html, re.I)
print(f"Total links: {len(links)}")
for l, t in links:
    clean = re.sub(r'<[^>]+>', '', t).strip()
    if clean:
        print(f"  [{clean}] -> {l}")
