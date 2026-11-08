from bs4 import BeautifulSoup

with open(r'C:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub\data\raw\lis\samples\user_apa_128_comp_success.html', 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')
title = soup.title.string if soup.title else 'No title'
print("Title:", title)

# Look for text like '對照表', '修正草案', '條文對照表', '說明'
for h in soup.find_all(['h1', 'h2', 'h3', 'h4', 'th', 'caption']):
    txt = h.get_text(strip=True)
    if any(k in txt for k in ['對照', '說明', '修正條文', '現行條文']):
        print("Header:", txt.encode('ascii', 'backslashreplace').decode('ascii'))

