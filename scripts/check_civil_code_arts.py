import json
import re

with open(r'C:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub\data\ChLaw.json', 'r', encoding='utf-8-sig') as f:
    data = json.load(f)

for law in data.get('Laws', []):
    if law.get('LawName') == '民法':
        arts = law.get('LawArticles', [])
        # filter actual articles
        real_arts = [a for a in arts if a.get('ArticleType') == 'A']
        print(f"Total entries in LawArticles: {len(arts)}")
        print(f"ArticleType == 'A': {len(real_arts)}")
        if real_arts:
            print("First 3:", [a.get('ArticleNo') for a in real_arts[:3]])
            print("Last 3:", [a.get('ArticleNo') for a in real_arts[-3:]])

