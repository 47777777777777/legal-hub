with open(r'C:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub\scripts\check_r2_links.py', 'r') as f:
    pass

import requests
from bs4 import BeautifulSoup

sess = requests.Session()
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
r1 = sess.get('https://lis.ly.gov.tw/lglawc/lglawkm', headers=headers)
r2 = sess.post('https://lis.ly.gov.tw/lglawc/lglawkm', data={'ACTNM': '行政程序法', 'button': '查詢'}, headers=headers)

soup = BeautifulSoup(r2.text, 'html.parser')
for a in soup.find_all('a', href=True):
    href = a['href']
    if 'lawsingle' in href or 'lglawkm?' in href:
        print("Link:", href, "Text:", a.get_text(strip=True)[:30])

