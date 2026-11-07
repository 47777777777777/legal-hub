import urllib.request
import sys

sys.stdout.reconfigure(encoding='utf-8')
headers = {'User-agent': 'Googlebot'}
try:
    req = urllib.request.Request('https://lawplayer.com/.well-known/ai-plugin.json', headers=headers)
    with urllib.request.urlopen(req, timeout=5) as resp:
        print(resp.read().decode('utf-8'))
except Exception as e:
    print(e)

