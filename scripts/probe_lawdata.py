import urllib.request
import ssl
import sys

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

cookies = sys.argv[1] if len(sys.argv) > 1 else 'sessionid=dqw2tstphy5qeoewvgg55jvo'
url = 'https://www-lawdata-com-tw.autorpa.lib.ccu.edu.tw:8443/'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Cookie': cookies})
try:
    with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
        print('Status:', r.status)
        print('Final URL:', r.url)
        content = r.read().decode('utf-8', errors='ignore')
        print('Length:', len(content))
        print('Title:', [line for line in content.splitlines() if '<title>' in line.lower()][:1])
        print('Sample:', content[:300])
except Exception as e:
    print('Error:', e)
