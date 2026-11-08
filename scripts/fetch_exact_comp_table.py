import requests
from bs4 import BeautifulSoup
import re

sess = requests.Session()
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# 1. Start session at lglawkm
r1 = sess.get('https://lis.ly.gov.tw/lglawc/lglawkm', headers=headers)
print("Step 1 status:", r1.status_code)

# 2. Search for 行政程序法
payload = {
    'ACTNM': '行政程序法',
    'button': '查詢'
}
r2 = sess.post('https://lis.ly.gov.tw/lglawc/lglawkm', data=payload, headers=headers)
print("Step 2 status:", r2.status_code)

# Find lawsingle links
m = re.search(r'href=["\'](/lglawc/lawsingle\?[^"\']+)["\']', r2.text)
if m:
    link = m.group(1)
    print("Found link:", link)
    token = link.split('?')[1][:10]
    print("Token:", token)
    
    # The user URL had view code: 0000000000000005A00000000C00FFFFFD00^01830109123000^00000000000
    # Let's try fetching with current token + user suffix:
    user_suffix = '0000000000000005A00000000C00FFFFFD00^01830109123000^00000000000'
    target_url = f"https://lis.ly.gov.tw/lglawc/lawsingle?00{token}{user_suffix}"
    print("Fetching target URL:", target_url)
    r3 = sess.get(target_url, headers=headers)
    print("Target status:", r3.status_code, "Length:", len(r3.text))
    
    with open(r'C:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub\data\raw\lis\samples\user_apa_128_comparison_page.html', 'w', encoding='utf-8') as f:
        f.write(r3.text)
        
    soup = BeautifulSoup(r3.text, 'html.parser')
    for table in soup.find_all('table'):
        t_text = table.get_text()
        if '一百二十八' in t_text or '128' in t_text:
            print("Found table with 128! Rows:", len(table.find_all('tr')))
            for row in table.find_all('tr')[:5]:
                cells = [c.get_text(strip=True) for c in row.find_all(['td', 'th'])]
                print("  Row cells:", [c[:50] for c in cells])

