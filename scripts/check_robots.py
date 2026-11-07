import urllib.request
import re
import sys
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding='utf-8')

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) LegalHub/1.0'}

# 1. Fetch sitemap index or rss
# Check robots.txt first
req = urllib.request.Request('https://lawplayer.com/robots.txt', headers=headers)
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        print("--- ROBOTS.TXT ---")
        print(resp.read().decode('utf-8'))
        print("------------------")
except Exception as e:
    print("robots.txt error:", e)

