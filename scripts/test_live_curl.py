import urllib.request
import ssl
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

ctx = ssl._create_unverified_context()
url = 'https://www-lawdata-com-tw.autorpa.lib.ccu.edu.tw:8443/anglekmc/ttswebx?@0:0:1:lawkm@@0.07765114904886061'
cookie = '_ga=GA1.1.1983743490.1793438764; _ga_WGHCEJZQV6=GS2.1.s1793489133$o2$g0$t1793489133$j60$l0$h0; flysheet-proxy=5963b762-9c6e-441b-a00a-c191e6adbdfd; lbkf=d0d5f061-0458-4ac6-ac8c-151522ede2da; lawbank=be5c468097bd41fea959b93e76e2cb3b-30; _ga_92YN8QGDF5=GS2.1.s1793493940$o2$g1$t1793493972$j28$l0$h0; _ga_BQBPZWYZE0=GS2.1.s1793493574$o5$g1$t1793495496$j58$l0$h0'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36',
    'Cookie': cookie,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://www-lawdata-com-tw.autorpa.lib.ccu.edu.tw:8443/anglekmc/ttswebx?@lawkm'
}

req = urllib.request.Request(url, headers=headers)
try:
    with urllib.request.urlopen(req, context=ctx, timeout=12) as resp:
        print('HTTP Status:', resp.status)
        raw = resp.read()
        print('Raw bytes len:', len(raw))
        html = None
        for enc in ('utf-8', 'cp950', 'big5'):
            try:
                html = raw.decode(enc)
                print(f'Successfully decoded with {enc}!')
                break
            except Exception:
                pass
        if not html:
            html = raw.decode('utf-8', errors='ignore')
            
        print('First 600 chars:\n', html[:600])
        titles = re.findall(r'<title>(.*?)</title>', html, re.I)
        print('Title:', titles)
        
        # Check inputs and forms
        forms = re.findall(r'<form[\s\S]*?</form>', html, re.I)
        print(f'Found {len(forms)} forms.')
        for i, f in enumerate(forms):
            action_m = re.search(r'action=[\"\']?([^\s\"\'>]+)', f, re.I)
            name_m = re.search(r'name=[\"\']?([^\s\"\'>]+)', f, re.I)
            action = action_m.group(1) if action_m else 'None'
            name = name_m.group(1) if name_m else 'None'
            print(f'Form {i}: name={name}, action={action}')
            inputs = re.findall(r'<input[\s\S]*?>', f, re.I)
            print(f'  Inputs ({len(inputs)}):', inputs[:8])
            
        # Save sample to scratch
        with open('scripts/lawdata_sample.html', 'w', encoding='utf-8') as out:
            out.write(html)
        print('Saved sample HTML to scripts/lawdata_sample.html')
except Exception as e:
    print('Error:', e)

