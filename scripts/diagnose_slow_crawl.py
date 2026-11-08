import time
import sys
import os

BASE_DIR = r"C:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub"
sys.path.insert(0, BASE_DIR)

from scripts.lis_crawler_pipeline import LisCrawler

crawler = LisCrawler()

# Test one law that took long
law_name = "國家運動科學中心設置條例"
act_id = "h0000185"
pcode = "H0000185"

print(f"=== Diagnosing bottleneck on {law_name} ===")

t0 = time.time()
entry_url = "https://lis.ly.gov.tw/lglawc/lglawkm"
s1, b1, _ = crawler.fetch_url(entry_url)
t1 = time.time()
print(f"Step 1 (Entry page): {round(t1 - t0, 2)}s, size: {len(b1)} B")

from bs4 import BeautifulSoup
import urllib.parse
soup1 = BeautifulSoup(b1.decode('utf-8', errors='ignore'), 'html.parser')
form = soup1.find('form')
action = form.get('action', '/lglawc/lglawkm') if form else '/lglawc/lglawkm'
if not action.startswith('http'):
    action = f"https://lis.ly.gov.tw{action}"
info_val = form.find('input', {'name': 'INFO'}).get('value', '') if form and form.find('input', {'name': 'INFO'}) else ''

post_data = {
    'INFO': info_val,
    '@_1_6_T': 'T_LN/LW',
    '_1_6_T': law_name,
    '_IMG_檢索.x': '10',
    '_IMG_檢索.y': '10'
}
encoded = urllib.parse.urlencode(post_data).encode('utf-8')
t2 = time.time()
s2, b2, u2 = crawler.fetch_url(action, data=encoded, headers={"Content-Type": "application/x-www-form-urlencoded", "Referer": entry_url})
t3 = time.time()
print(f"Step 2 (POST Search): {round(t3 - t2, 2)}s, size: {len(b2)} B")

html2 = b2.decode('utf-8', errors='ignore')
soup2 = BeautifulSoup(html2, 'html.parser')

history_link = None
for a in soup2.find_all('a'):
    txt = a.get_text(strip=True)
    if '法條沿革' in txt:
        history_link = a.get('href')
        break

print(f"Direct history_link found: {bool(history_link)}")

if not history_link:
    print("Searching in search result table links...")
    for a in soup2.find_all('a'):
        txt = a.get_text(strip=True)
        href = a.get('href', '')
        if (law_name in txt or txt == law_name) and 'lawsingle' in href:
            law_link = href if href.startswith('http') else f"https://lis.ly.gov.tw{href}"
            t_sub0 = time.time()
            s_sub, b_sub, _ = crawler.fetch_url(law_link)
            t_sub1 = time.time()
            print(f"  Followed law_link: {round(t_sub1 - t_sub0, 2)}s")
            soup_sub = BeautifulSoup(b_sub.decode('utf-8', errors='ignore'), 'html.parser')
            for a_h in soup_sub.find_all('a'):
                if '法條沿革' in a_h.get_text(strip=True):
                    history_link = a_h.get('href')
                    break
            break

if history_link:
    if not history_link.startswith('http'):
        history_link = f"https://lis.ly.gov.tw{history_link}"
    t4 = time.time()
    s3, b3, u3 = crawler.fetch_url(history_link)
    t5 = time.time()
    print(f"Step 3 (Fetch Fullpage): {round(t5 - t4, 2)}s, size: {len(b3)} B")

print(f"Total time taken: {round(time.time() - t0, 2)}s")

