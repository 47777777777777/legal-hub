import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
raw_dir = os.path.join(BASE_DIR, 'data', 'raw', 'lawplayer', 'civil_procedure_code')
cpc_act_path = os.path.join(raw_dir, 'cpc_act.body.html')

with open(cpc_act_path, 'r', encoding='utf-8') as f:
    html = f.read()

from bs4 import BeautifulSoup
soup = BeautifulSoup(html, 'html.parser')

links = soup.find_all('a', href=re.compile(r'^/article/[a-f0-9]+'))
for a in links:
    txt = a.get_text(" ", strip=True)
    if '31' in txt or '77' in txt:
        print(a.get('href'), '->', txt)

