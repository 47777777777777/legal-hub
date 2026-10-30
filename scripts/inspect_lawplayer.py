import urllib.request
import re
import json

url = 'https://lawplayer.com/act/6437d05ae800e5f0b9301656'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
with urllib.request.urlopen(req, timeout=15) as resp:
    html = resp.read().decode('utf-8')

match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html)
if match:
    data = json.loads(match.group(1))
    print('NEXT_DATA keys:', data.keys())
    props = data.get('props', {})
    page_props = props.get('pageProps', {})
    print('pageProps keys:', page_props.keys())
    for k, v in page_props.items():
        print(f"  {k}: {type(v)}")
        if isinstance(v, dict):
            print(f"    subkeys: {list(v.keys())[:10]}")
else:
    print('No __NEXT_DATA__')
    # search for api endpoints in html
    apis = set(re.findall(r'https?://[^\s"\'<>]+api[^\s"\'<>]*', html))
    print('APIs found in html:', apis)
    endpoints = set(re.findall(r'/api/[^\s"\'<>]+', html))
    print('Internal endpoints:', endpoints)

