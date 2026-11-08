import sys
import urllib.request
from http.cookiejar import CookieJar
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

# Re-run the flow and fetch Art 128
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

# Find the Art 128 link
art128_link = None
for a in soup3.find_all('a'):
    href = a.get('href', '')
    if '012800' in href:
        art128_link = href
        break

print("Found Art 128 Link:", art128_link)
if not art128_link.startswith('http'):
    art128_link = f"https://lis.ly.gov.tw{art128_link}"

with opener.open(urllib.request.Request(art128_link, headers={"User-Agent": "Mozilla/5.0"})) as r:
    raw_128 = r.read()

out_path = "data/raw/lis/samples/apa_128_lis_page.html"
with open(out_path, "wb") as f:
    f.write(raw_128)

print(f"Saved Art 128 page ({len(raw_128)} bytes) to {out_path}")
soup_128 = BeautifulSoup(raw_128.decode('utf-8', errors='ignore'), 'html.parser')
print("\nPage title:", soup_128.title.get_text() if soup_128.title else "")

# Inspect text in the page
print("\n--- Art 128 Page Content Snippet ---")
print(soup_128.get_text()[:600].replace('\n', ' '))

