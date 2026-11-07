with open('C:/Users/harry/.gemini/antigravity-ide/scratch/legal-hub/scripts/test_antiproxy.py', 'r') as f:
    pass

import urllib.request
import ssl
import sys

sys.stdout.reconfigure(encoding='utf-8')
ctx = ssl._create_unverified_context()
cookie = 'flysheet-proxy=5963b762-9c6e-441b-a00a-c191e6adbdfd; lbkf=d0d5f061-0458-4ac6-ac8c-151522ede2da; lawbank=be5c468097bd41fea959b93e76e2cb3b-30'

url = 'https://www-lawdata-com-tw.autorpa.lib.ccu.edu.tw:8443/anglekmc/ttswebx'
req = urllib.request.Request(url, headers={'Cookie': cookie, 'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
    print(r.read().decode('utf-8', errors='replace'))

