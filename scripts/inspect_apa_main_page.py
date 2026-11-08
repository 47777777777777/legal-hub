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

# 2. Search
post_data = {
    'INFO': info_val,
    '@_1_6_T': 'T_LN/LW',
    '_1_6_T': '行政程序法',
    '_IMG_檢索.x': '10',
    '_IMG_檢索.y': '10'
}
encoded = urllib.parse.urlencode(post_data).encode('utf-8')
req2 = urllib.request.Request(action, data=encoded, headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/x-www-form-urlencoded"})
with opener.open(req2) as resp:
    html2 = resp.read().decode('utf-8', errors='ignore')

# 3. Main law page
soup2 = BeautifulSoup(html2, 'html.parser')
act_link = None
for a in soup2.find_all('a'):
    if a.get_text(strip=True) == '行政程序法' and 'lawsingle' in a.get('href', ''):
        act_link = a.get('href')
        break

if not act_link.startswith('http'):
    act_link = f"https://lis.ly.gov.tw{act_link}"

req3 = urllib.request.Request(act_link, headers={"User-Agent": "Mozilla/5.0"})
with opener.open(req3) as resp:
    html3 = resp.read().decode('utf-8', errors='ignore')

soup3 = BeautifulSoup(html3, 'html.parser')
print("=== Links & Buttons on 行政程序法 main page ===")
for a in soup3.find_all('a'):
    txt = a.get_text(strip=True)
    href = a.get('href', '')
    img = a.find('img')
    img_alt = img.get('alt', '') if img else ''
    label = txt or img_alt or a.get('title', '')
    if any(k in label or k in href for k in ['沿革', '理由', '對照', '條文', '109', '128', 'comp', 'law']):
        print(f"[{label}] -> {href}")

# Check any forms on main page
for f in soup3.find_all('form'):
    print(f"Form action={f.get('action')}, name={f.get('name')}")
    for inp in f.find_all('input'):
        if inp.get('type') != 'hidden':
            print(f"   input name={inp.get('name')}, type={inp.get('type')}, value={inp.get('value')}")

