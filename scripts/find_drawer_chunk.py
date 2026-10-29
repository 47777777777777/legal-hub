import urllib.request
import re

url = 'https://lawplayer.com/act/6437d05ae800e5f0b9301656'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=10) as resp:
    html = resp.read().decode('utf-8', errors='ignore')

chunk_urls = set(re.findall(r'/_next/static/chunks/[a-zA-Z0-9/_.-]+\.js', html))
print(f'Found {len(chunk_urls)} chunk URLs')

for curl in list(chunk_urls):
    full_url = 'https://lawplayer.com' + curl
    try:
        with urllib.request.urlopen(full_url, timeout=5) as cresp:
            js = cresp.read().decode('utf-8', errors='ignore')
            if 'ActArticleDrawer' in js or '關鍵知識' in js or '白話與解析' in js:
                print(f'Match found in {curl}!')
                # Look for API calls or endpoints
                apis = set(re.findall(r'[`\'"](/api/[^`\'"]+)[`\'"]', js))
                print('  APIs in this chunk:', apis)
                # Look for external endpoints
                exts = set(re.findall(r'https://api\.[^`\'"]+', js))
                print('  Ext APIs:', exts)
    except Exception as e:
        pass
