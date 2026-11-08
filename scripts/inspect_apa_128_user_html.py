from bs4 import BeautifulSoup

with open(r'C:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub\data\raw\lis\samples\user_apa_128_comp_success.html', 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')
tables = soup.find_all('table')
print(f"Tables count: {len(tables)}, html length: {len(html)}")

for i, t in enumerate(tables):
    rows = t.find_all('tr')
    print(f"Table {i}: {len(rows)} rows")
    for r in rows[:4]:
        cells = [c.get_text(strip=True) for c in r.find_all(['th', 'td'])]
        print("  Row:", cells)

