import urllib.request
import sys

sys.stdout.reconfigure(encoding='utf-8')
headers = {'User-agent': 'Googlebot'}
for path in ['/llms.txt', '/.well-known/ai-plugin.json']:
    try:
        req = urllib.request.Request('https://lawplayer.com' + path, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            print(f"--- {path} ---")
            print(resp.read().decode('utf-8')[:1000])
    except Exception as e:
        print(f"{path} error: {e}")

