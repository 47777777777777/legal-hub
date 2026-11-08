from bs4 import BeautifulSoup

with open(r'C:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub\data\raw\lis\samples\user_apa_128_comp_success.html', 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')
for i, tr in enumerate(soup.find_all('tr')):
    text = tr.get_text()
    if '第一百二十八條' in text and ('一、本項新增' in text or '修正條文' in text or '現行條文' in text or '說明' in text):
        print(f"--- TR {i} ---")
        for j, td in enumerate(tr.find_all(['td', 'th'])):
            print(f"  Col {j}:", td.get_text(strip=True)[:100])

