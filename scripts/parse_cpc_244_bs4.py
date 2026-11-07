import os
import re
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
raw_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'raw', 'lawplayer', 'civil_procedure_code')

with open(os.path.join(raw_dir, 'cpc_art_244.body.html'), 'r', encoding='utf-8') as f:
    html = f.read()

from bs4 import BeautifulSoup
soup = BeautifulSoup(html, 'html.parser')

h1 = soup.find('h1', class_='artw-title')
print("H1 title:", h1.get_text(strip=True) if h1 else None)
sum_span = soup.find('span', class_='artw-title-sum')
print("Title sum span:", sum_span.get_text(strip=True) if sum_span else None)

interp_section = soup.find('section', id='w-interp')
print("\nw-interp section found?", interp_section is not None)
if interp_section:
    for li in interp_section.find_all('li', class_='artw-interp-row'):
        title = li.find('a', class_='artw-interp-title')
        meta = li.find('span', class_='artw-interp-meta')
        href = title.get('href') if title else None
        ref_text = title.get_text(strip=True) if title else None
        meta_text = meta.get_text(" ", strip=True) if meta else None
        print(f"  Row: href={href}, ref={ref_text}, meta={meta_text}")

