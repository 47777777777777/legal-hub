import json

with open(r'C:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub\data\ChLaw.json', 'r', encoding='utf-8-sig') as f:
    data = json.load(f)

laws = data.get('Laws', [])
print("Total laws in ChLaw.json:", len(laws))

for law in laws:
    name = law.get('LawName', '')
    pcode = law.get('LawPcode', '')
    if name in ['國家賠償法', '消費者保護法', '營業秘密法', '涉外民事法律適用法', '司法院釋字第七四八號解釋施行法', '行政訴訟法', '懲治走私條例', '民法']:
        articles = law.get('LawArticles', [])
        print(f"LawName: {name}, LawPcode: {pcode}, Articles: {len(articles)}")

