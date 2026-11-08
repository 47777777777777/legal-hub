with open(r'C:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub\data\raw\lis\samples\user_apa_128_comp_success.html', 'r', encoding='utf-8') as f:
    html = f.read()

import re
print("Matches for 對照:", len(re.findall(r'對照', html)))
print("Matches for 說明:", len(re.findall(r'說明', html)))
print("Matches for 修正條文:", len(re.findall(r'修正條文', html)))
print("Matches for 現行條文:", len(re.findall(r'現行條文', html)))
print("Matches for 1091230:", len(re.findall(r'1091230', html)))

pos = html.find('1091230')
while pos != -1:
    snippet = html[max(0, pos-50):pos+150]
    # replace newlines
    snippet = ' '.join(snippet.split())
    print("Snippet around 1091230:", snippet.encode('ascii', 'backslashreplace').decode('ascii'))
    pos = html.find('1091230', pos+1)

