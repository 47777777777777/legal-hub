import urllib.request
import ssl
import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

ctx = ssl._create_unverified_context()
cookie = '_ga=GA1.1.1983743490.1793438764; _ga_WGHCEJZQV6=GS2.1.s1793489133$o2$g0$t1793489133$j60$l0$h0; flysheet-proxy=5963b762-9c6e-441b-a00a-c191e6adbdfd; lbkf=d0d5f061-0458-4ac6-ac8c-151522ede2da; lawbank=be5c468097bd41fea959b93e76e2cb3b-30; _ga_92YN8QGDF5=GS2.1.s1793493940$o2$g1$t1793493972$j28$l0$h0; _ga_BQBPZWYZE0=GS2.1.s1793493574$o5$g1$t1793495496$j58$l0$h0'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36',
    'Cookie': cookie,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://www-lawbank-com-tw.autorpa.lib.ccu.edu.tw:8443/index.aspx'
}

req = urllib.request.Request('https://www-lawbank-com-tw.autorpa.lib.ccu.edu.tw:8443/treatise/query.aspx', headers=headers)
with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
    html = resp.read().decode('utf-8', errors='ignore')
    print('Treatise Query Status:', resp.status, 'Length:', len(html))
    # Find form actions and input names
    forms = re.findall(r'<form[^>]*action=["\']?([^\s"\'>]+)["\']?[^>]*>', html, re.I)
    print('Forms:', forms)
    inputs = re.findall(r'<input[^>]*name=["\']?([^\s"\'>]+)["\']?[^>]*>', html, re.I)
    print('Inputs:', inputs[:15])
    selects = re.findall(r'<select[^>]*name=["\']?([^\s"\'>]+)["\']?[^>]*>', html, re.I)
    print('Selects:', selects)
    
    with open('C:/Users/harry/.gemini/antigravity-ide/scratch/legal-hub/scripts/lawbank_treatise.html', 'w', encoding='utf-8') as f:
        f.write(html)

