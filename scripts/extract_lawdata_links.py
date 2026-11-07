import urllib.request
import re
import ssl

ctx = ssl._create_unverified_context()

urls_to_check = [
    "https://law.nccu.edu.tw",
    "https://www.law.ntu.edu.tw",
]
for u in urls_to_check:
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=8) as r:
            html = r.read().decode("utf-8", errors="ignore")
            matches = re.findall(r'https?://(?:www\.)?lawdata\.com\.tw[^\s"\'<>]*', html)
            if matches:
                print(f"From {u}:", matches[:5])
    except Exception as e:
        print(f"Error {u}: {e}")
