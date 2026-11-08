import sys
import urllib.request
import urllib.parse
from http.cookiejar import CookieJar
from bs4 import BeautifulSoup
import re

sys.stdout.reconfigure(encoding='utf-8')

cj = CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# 1. Entry
entry_url = "https://lis.ly.gov.tw/lglawc/lglawkm"
req1 = urllib.request.Request(entry_url, headers={"User-Agent": "Mozilla/5.0"})
with opener.open(req1) as resp:
    html1 = resp.read().decode('utf-8', errors='ignore')

soup1 = BeautifulSoup(html1, 'html.parser')
info_inp = soup1.find('input', {'name': 'INFO'})
info_val = info_inp.get('value', '') if info_inp else ''
form = soup1.find('form')
action = form.get('action') if form else entry_url
if not action.startswith('http'):
    action = f"https://lis.ly.gov.tw{action}"

# 2. Search 民法
post_data = {
    'INFO': info_val,
    '@_1_6_T': 'T_LN/LW',
    '_1_6_T': '民法',
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

soup2 = BeautifulSoup(html2, 'html.parser')
print("=== Search Results for '民法' on LIS ===")
for a in soup2.find_all('a'):
    txt = a.get_text(strip=True)
    href = a.get('href', '')
    if 'lawsingle' in href or '民法' in txt:
        print(f"Text: '{txt}' -> Link: {href[:80]}")

