import sys
import json
import sqlite3
import os

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHLAW_PATH = os.path.join(BASE_DIR, "data", "ChLaw.json")
DB_PATH = os.path.join(BASE_DIR, "data", "legal_hub.db")

print("=== 1. Checking PCode in ChLaw.json ===")
with open(CHLAW_PATH, 'r', encoding='utf-8-sig') as f:
    laws = json.load(f)['Laws']

pcodes_to_check = ['A0030154', 'B0000001', 'A0030101', 'J0100001', 'A0030055', 'C0000001', 'B0010001', 'C0010001', 'N0030001', 'J0080001', 'K0040012']
found = {}
for l in laws:
    p = l.get('PCode')
    if p in pcodes_to_check:
        found[p] = (l.get('LawName'), len(l.get('LawArticles', [])))

for p in pcodes_to_check:
    print(f"PCode {p}: {found.get(p)}")

# Also search for '懲治走私條例' and '行政訴訟法' in ChLaw.json
print("\n=== Search Law Names in ChLaw.json ===")
for l in laws:
    name = l.get('LawName', '')
    p = l.get('PCode')
    if name in ('懲治走私條例', '行政訴訟法', '國家賠償法', '消費者保護法', '營業秘密法', '涉外民事法律適用法', '司法院釋字第七四八號解釋施行法', '民法'):
        print(f"Name '{name}' -> PCode: {p}, Articles: {len(l.get('LawArticles', []))}")

print("\n=== Check acts table for A0030154 ===")
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("SELECT id, name, pcode FROM acts WHERE pcode = 'A0030154' OR id = 'a0030154'")
print("acts query for A0030154:", cur.fetchall())

cur.execute("SELECT id, name, pcode FROM acts WHERE name LIKE '%行政訴訟%' OR name LIKE '%走私%'")
print("acts query for 行政訴訟 / 走私:", cur.fetchall())

conn.close()
