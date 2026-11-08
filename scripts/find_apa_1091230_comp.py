import sys
import urllib.request
import urllib.parse
from http.cookiejar import CookieJar
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

cj = CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# 1. Entry
entry_url = "https://lis.ly.gov.tw/lglawc/lglawkm"
req1 = urllib.request.Request(entry_url, headers={"User-Agent": "Mozilla/5.0"})
with opener.open(req1) as resp:
    html1 = resp.read().decode('utf-8', errors='ignore')

soup1 = BeautifulSoup(html1, 'html.parser')
info_val = soup1.find('input', {'name': 'INFO'}).get('value', '')
form = soup1.find('form')
action = form.get('action') if form else entry_url
if not action.startswith('http'):
    action = f"https://lis.ly.gov.tw{action}"

# 2. Search 行政程序法
post_data = {
    'INFO': info_val,
    '@_1_6_T': 'T_LN/LW',
    '_1_6_T': '行政程序法',
    '_IMG_檢索.x': '10',
    '_IMG_檢索.y': '10'
}
encoded = urllib.parse.urlencode(post_data).encode('utf-8')
req2 = urllib.request.Request(
    action, data=encoded,
    headers={
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": entry_url
    }
)
with opener.open(req2) as resp:
    html2 = resp.read().decode('utf-8', errors='ignore')

# 3. Now try fetching the user's target URL in this active session
target_url = "https://lis.ly.gov.tw/lglawc/lawsingle?00131F01CA74000000000000000005A00000000C00FFFFFD00^01830109123000^00000000000"
req3 = urllib.request.Request(
    target_url,
    headers={
        "User-Agent": "Mozilla/5.0",
        "Referer": action
    }
)
try:
    with opener.open(req3) as resp:
        raw3 = resp.read()
    txt3 = raw3.decode('utf-8', errors='ignore')
    print("In-session fetch size:", len(raw3))
    print("Session expired?", "超過系統設定" in txt3)
    if "超過系統設定" not in txt3:
        with open("data/raw/lis/samples/user_apa_128_comp.html", "wb") as f:
            f.write(raw3)
        print("Successfully saved user comparison page to data/raw/lis/samples/user_apa_128_comp.html")
except Exception as e:
    print("Error:", e)

# 4. Also inspect search results HTML to see what comparison links exist for 行政程序法
soup2 = BeautifulSoup(html2, 'html.parser')
print("\nLinks found on 行政程序法 search page:")
for a in soup2.find_all('a'):
    txt = a.get_text(strip=True)
    href = a.get('href', '')
    if '對照' in txt or '1091230' in href or 'lawsingle' in href:
        print(f"[{txt}] -> {href}")

