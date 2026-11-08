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
with opener.open(urllib.request.Request(entry_url, headers={"User-Agent": "Mozilla/5.0"})) as r:
    h1 = r.read().decode('utf-8', errors='ignore')

info_val = BeautifulSoup(h1, 'html.parser').find('input', {'name': 'INFO'}).get('value', '')
action = "https://lis.ly.gov.tw/lglawc/lglawkm"

# 2. Search
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
if not act_link.startswith('http'):
    act_link = f"https://lis.ly.gov.tw{act_link}"

# 3. Main law page
with opener.open(urllib.request.Request(act_link, headers={"User-Agent": "Mozilla/5.0"})) as r:
    h3 = r.read().decode('utf-8', errors='ignore')

soup3 = BeautifulSoup(h3, 'html.parser')

# Find the 1091230 link
target_link = None
for a in soup3.find_all('a'):
    txt = a.get_text(strip=True)
    if '109年12月30日' in txt:
        target_link = a.get('href')
        print(f"Found target link for '{txt}': {target_link}")
        break

if not target_link.startswith('http'):
    target_link = f"https://lis.ly.gov.tw{target_link}"

with opener.open(urllib.request.Request(target_link, headers={"User-Agent": "Mozilla/5.0"})) as r:
    raw_target = r.read()

soup_target = BeautifulSoup(raw_target.decode('utf-8', errors='ignore'), 'html.parser')
print("\nTarget page text snippet:")
print(soup_target.get_text()[:600].replace('\n', ' '))

print("\nLinks on 1091230 page:")
for a in soup_target.find_all('a'):
    t = a.get_text(strip=True)
    h = a.get('href', '')
    img = a.find('img')
    img_alt = img.get('alt', '') if img else ''
    print(f"[{t or img_alt}] -> {h}")

