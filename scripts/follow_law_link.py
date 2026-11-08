import requests
from bs4 import BeautifulSoup

sess = requests.Session()
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
r1 = sess.get('https://lis.ly.gov.tw/lglawc/lglawkm', headers=headers)
r2 = sess.post('https://lis.ly.gov.tw/lglawc/lglawkm', data={'ACTNM': '行政程序法', 'button': '查詢'}, headers=headers)

soup = BeautifulSoup(r2.text, 'html.parser')
law_link = None
for a in soup.find_all('a', href=True):
    if '行政程序法' in a.get_text():
        law_link = a['href']
        break

print("Law link:", law_link)
if law_link:
    r3 = sess.get('https://lis.ly.gov.tw' + law_link, headers=headers)
    print("r3 status:", r3.status_code, "len:", len(r3.text))
    # In r3, find buttons/links: '對照表', '法條沿革', etc.
    soup3 = BeautifulSoup(r3.text, 'html.parser')
    for a in soup3.find_all('a', href=True):
        txt = a.get_text(strip=True)
        img = a.find('img')
        img_src = img['src'] if img and img.has_attr('src') else ''
        if any(k in txt for k in ['對照', '沿革', '理由']) or any(k in img_src for k in ['btn', 'relate']):
            print(f"Option: text={repr(txt)}, img={img_src}, href={a['href']}")

