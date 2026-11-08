import sys
import urllib.request
from http.cookiejar import CookieJar
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

cj = CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# 1. First visit main page to initialize session
entry_url = "https://lis.ly.gov.tw/lglawc/lglawkm"
req1 = urllib.request.Request(entry_url, headers={"User-Agent": "Mozilla/5.0"})
with opener.open(req1) as resp:
    resp.read()

# 2. Now visit the target lawsingle comparison URL
target_url = "https://lis.ly.gov.tw/lglawc/lawsingle?00131F01CA74000000000000000005A00000000C00FFFFFD00^01830109123000^00000000000"
req2 = urllib.request.Request(
    target_url, 
    headers={
        "User-Agent": "Mozilla/5.0",
        "Referer": entry_url
    }
)
with opener.open(req2) as resp:
    raw = resp.read()

out_path = "data/raw/lis/samples/user_apa_128_comp.html"
with open(out_path, "wb") as f:
    f.write(raw)

txt = raw.decode('utf-8', errors='ignore')
print(f"Fetched size: {len(raw)} bytes")
print("Session expired?", "超過系統設定" in txt)

if "超過系統設定" not in txt:
    print("SUCCESS! Page title and contents:")
    soup = BeautifulSoup(txt, 'html.parser')
    print("Title:", soup.title.get_text() if soup.title else "No title")
    # Search for 第一百二十八條 or 說明
    for td in soup.find_all('td'):
        t = td.get_text(strip=True)
        if '第一百二十八條' in t or '新證據' in t or '說明' in t:
            print(f"TD [{t[:150]}]")

