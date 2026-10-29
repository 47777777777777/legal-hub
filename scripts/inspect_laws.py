import json

with open('data/ChLaw.json', 'r', encoding='utf-8-sig') as f:
    data = json.load(f)

laws = data.get('Laws', [])
print('Total laws in ChLaw.json:', len(laws))

target_names = ['中華民國刑法', '民法', '中華民國憲法', '勞動基準法', '行政程序法', '道路交通管理處罰條例', '公司法', '刑事訴訟法', '民事訴訟法']
for law in laws:
    name = law.get('LawName', '')
    if name in target_names:
        arts = [a for a in law.get('LawArticles', []) if a.get('ArticleType') == 'A']
        chapters = [a for a in law.get('LawArticles', []) if a.get('ArticleType') == 'C']
        url = law.get('LawURL', '')
        pcode = url.split('=')[-1] if '=' in url else ''
        print(f"Name: {name:20s} | PCode: {pcode:10s} | Articles: {len(arts):4d} | Chapters: {len(chapters):3d}")

