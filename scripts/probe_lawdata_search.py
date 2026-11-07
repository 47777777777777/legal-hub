import urllib.request
import ssl
import random

ctx = ssl._create_unverified_context()
url = f"https://www.lawdata.com.tw/anglekmc/ttswebx?@0:0:1:lawkm@@{random.random()}"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
try:
    with urllib.request.urlopen(req, context=ctx, timeout=8) as r:
        html = r.read().decode("big5", errors="ignore")  # HyWeb often uses big5 or cp950
        print("Length:", len(html))
        # Print form blocks
        import re
        forms = re.findall(r'<form[\s\S]*?</form>', html, re.I)
        for i, f in enumerate(forms):
            print(f"--- FORM {i} ---")
            print(f[:2000])
except Exception as e:
    print("Error:", e)
