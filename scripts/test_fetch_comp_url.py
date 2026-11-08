import sys
import urllib.request
from http.cookiejar import CookieJar
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

cj = CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# 1. Entry & Search to initialize session
entry_url = "https://lis.ly.gov.tw/lglawc/lglawkm"
with opener.open(urllib.request.Request(entry_url, headers={"User-Agent": "Mozilla/5.0"})) as r:
    h1 = r.read().decode('utf-8', errors='ignore')

info_val = BeautifulSoup(h1, 'html.parser').find('input', {'name': 'INFO'}).get('value', '')
action = "https://lis.ly.gov.tw/lglawc/lglawkm"
post_data = urllib.parse.urlencode({
    'INFO': info_val,
    '@_1_6_T': 'T_LN/LW',
    '_1_6_T': '行政程序法',
    '_IMG_檢索.x': '10',
    '_IMG_檢索.y': '10'
}).encode('utf-8')

with opener.open(urllib.request.Request(action, data=post_data, headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/x-www-form-urlencoded"})) as r:
    h2 = r.read().decode('utf-8', errors='ignore')

soup2 = BeautifulSoup(h2, 'html.parser')
act_link = [a.get('href') for a in soup2.find_all('a') if a.get_text(strip=True) == '行政程序法'][0]
session_token = act_link.split('lawsingle?')[1].split('^')[0]
print("Session token from search:", session_token)
# The first 12 hex chars is session id:
sess_id = session_token[:12]
print("Sess ID:", sess_id)

# Construct the comparison URL:
# user URL was: 00131F01CA74 0000000000000000 05A00000000C00 FFFFFD00 ^ 01830109123000 ^ 00000000000
comp_url = f"https://lis.ly.gov.tw/lglawc/lawsingle?{sess_id}000000000000000005A00000000C00FFFFFD00^01830109123000^00000000000"
print("Attempting to fetch comp_url:", comp_url)

with opener.open(urllib.request.Request(comp_url, headers={"User-Agent": "Mozilla/5.0"})) as r:
    raw_comp = r.read()

comp_text = raw_comp.decode('utf-8', errors='ignore')
print("Fetched comp length:", len(raw_comp))
print("Session expired?", "超過系統設定" in comp_text)

if "超過系統設定" not in comp_text:
    out_file = "data/raw/lis/samples/user_apa_128_comp_success.html"
    with open(out_file, "wb") as f:
        f.write(raw_comp)
    print(f"Saved to {out_file}!")
    soup_comp = BeautifulSoup(comp_text, 'html.parser')
    print("Page Title:", soup_comp.title.get_text() if soup_comp.title else "")
    # Check tables
    for tr in soup_comp.find_all('tr'):
        tds = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
        if any('第一百二十八條' in t or '新證據' in t or '說明' in t for t in tds):
            print("Row:", tds[:3])

