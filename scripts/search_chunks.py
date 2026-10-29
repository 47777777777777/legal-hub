import urllib.request
import re

chunks = [
    '88429-3077a1e4.js',
    '28933-73ed6b4b.js',
    '39367-602ffee1.js',
    '6300-a449a8b0.js',
    '0359e3af-867862a4.js',
    'main-app-a3722857.js'
]

for c in chunks:
    url = f'https://lawplayer.com/_next/static/chunks/{c}'
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            text = resp.read().decode('utf-8', errors='ignore')
            # Look for endpoint pattern
            matches = set(re.findall(r'https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[a-zA-Z0-9_.-]+)*', text))
            apis = [m for m in matches if 'lawplayer' in m or 'api' in m]
            if apis:
                print(f'{c} has endpoints:', apis)
            # Look for drawer or tab logic
            if '關鍵知識' in text or '立法理由' in text or '內容連結' in text:
                print(f'{c} has legal tabs!')
    except Exception as e:
        print(f'Error fetching {c}:', e)
