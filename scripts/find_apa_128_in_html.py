from bs4 import BeautifulSoup
import re

with open(r'C:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub\data\raw\lis\samples\user_apa_128_comp_success.html', 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')
found = []
for tr in soup.find_all('tr'):
    text = tr.get_text()
    if '一百二十八' in text or '128' in text:
        cells = [c.get_text(strip=True) for c in tr.find_all(['th', 'td'])]
        found.append(cells)

print(f"Found {len(found)} rows mentioning 128/一百二十八:")
for f in found:
    print("--- ROW ---")
    for cell in f:
        print("  [CELL]:", cell[:100].encode('ascii', 'backslashreplace').decode('ascii'))

