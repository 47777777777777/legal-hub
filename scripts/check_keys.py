import json

with open(r'C:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub\data\ChLaw.json', 'r', encoding='utf-8-sig') as f:
    data = json.load(f)

laws = data.get('Laws', [])
for law in laws[:1]:
    print("Keys in law:", list(law.keys()))
    for k in ['LawName', 'Pcode', 'LawPcode', 'LawURL']:
        print(f"  {k}: {law.get(k)}")

for law in laws:
    name = law.get('LawName', '')
    if name in ['國家賠償法', '消費者保護法', '營業秘密法', '涉外民事法律適用法', '司法院釋字第七四八號解釋施行法', '行政訴訟法', '懲治走私條例', '民法']:
        pcode = law.get('Pcode') or law.get('LawPcode') or law.get('LawUrl', '')
        print(f"{name.encode('ascii', 'backslashreplace').decode('ascii')}: {law.get('LawLevel', '')} / {pcode} / {law.get('LawModifiedDate')}")

