import os
import re
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
raw_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'raw', 'lawplayer', 'civil_procedure_code')

for name in ['civil_art_2.rsc.json', 'cpc_art_244.rsc.json']:
    with open(os.path.join(raw_dir, name), 'r', encoding='utf-8') as f:
        rsc = f.read()
    
    print(f"\n====================== {name} ======================")
    # Look for /rule/ matches
    rule_ids = list(set(re.findall(r'/rule/([a-f0-9]+)', rsc)))
    print(f"Unique rule IDs found: {len(rule_ids)}")
    for rid in rule_ids:
        pos = rsc.find(rid)
        snippet = rsc[max(0, pos-50):pos+400]
        # print snippet
        print(f"Rule {rid}:")
        print("  Snippet:", repr(snippet[:250]))

