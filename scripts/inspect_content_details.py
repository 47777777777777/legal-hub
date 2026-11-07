import os
import re
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
raw_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'raw', 'lawplayer', 'civil_procedure_code')

for name in ['civil_art_2.rsc.json', 'cpc_art_244.rsc.json']:
    with open(os.path.join(raw_dir, name), 'r', encoding='utf-8') as f:
        rsc = f.read()
    
    print(f"\n================= {name} =================")
    # Search for summary / vernacular / Q&A / deep reading
    # Let's search for keywords:
    for kw in ['重點摘要', '白話', '深度閱讀', '沿革', '審級', '理由']:
        matches = [line for line in rsc.split('\n') if kw in line]
        print(f"Keyword '{kw}': {len(matches)} lines")
        for m in matches[:2]:
            print(f"  {m[:200]}...")

