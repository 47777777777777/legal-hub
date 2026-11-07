import urllib.request
import re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) LegalHub/1.0'}
for url in ['https://lawplayer.com', 'https://lawplayer.com/explore', 'https://lawplayer.com/category']:
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode('utf-8')
            print(f"{url} -> status {resp.status}, length {len(content)}")
            # look for civil procedure
            if "民事訴訟" in content:
                print(f"  FOUND '民事訴訟' in {url}!")
                for m in re.finditer(r'/act/([a-f0-9]+)', content):
                    print("  act id:", m.group(0))
    except Exception as e:
        print(f"{url} -> error: {e}")

