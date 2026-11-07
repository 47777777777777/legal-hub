import urllib.request
import urllib.parse
import ssl
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Cookie": "flysheet-proxy=2bad98fc-68c2-46d3-93bf-94559c48f4da"
}
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

print("=== 1. Probing LawData (Anglekmc) ===")
url1 = "https://www-lawdata-com-tw.autorpa.lib.ccu.edu.tw:8443/anglekmc/ttswebx?@lawkm"
try:
    req = urllib.request.Request(url1, headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        print("URL1 Final:", resp.url)
        html = resp.read().decode("utf-8", errors="ignore")
        print("URL1 Len:", len(html))
        t = re.search(r"<title>([^<]+)</title>", html, re.I)
        print("URL1 Title:", t.group(1) if t else "No title")
        # Print all input names and forms
        forms = re.findall(r'<form[^>]*>', html, re.I)
        print("Forms found:", forms[:3])
        inputs = re.findall(r'<input[^>]+name="([^"]+)"', html, re.I)
        print("Input names:", inputs[:10])
except Exception as e:
    print("URL1 Error:", e)

print("\n=== 2. Probing LawBank Treatise Query ===")
url2 = "https://www-lawbank-com-tw.autorpa.lib.ccu.edu.tw:8443/treatise/query.aspx"
try:
    req = urllib.request.Request(url2, headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        print("URL2 Final:", resp.url)
        html = resp.read().decode("utf-8", errors="ignore")
        print("URL2 Len:", len(html))
        t = re.search(r"<title>([^<]+)</title>", html, re.I)
        print("URL2 Title:", t.group(1) if t else "No title")
        inputs = re.findall(r'<input[^>]+name="([^"]+)"', html, re.I)
        print("LawBank Inputs:", inputs[:10])
except Exception as e:
    print("URL2 Error:", e)

print("\n=== 3. Probing LawBank Database Search (DB-LawBank FINT) ===")
url3 = "https://db-lawbank-com-tw.autorpa.lib.ccu.edu.tw:8443/FINT"
try:
    req = urllib.request.Request(url3, headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        print("URL3 Final:", resp.url)
        html = resp.read().decode("utf-8", errors="ignore")
        print("URL3 Len:", len(html))
        t = re.search(r"<title>([^<]+)</title>", html, re.I)
        print("URL3 Title:", t.group(1) if t else "No title")
except Exception as e:
    print("URL3 Error:", e)
