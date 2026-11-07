import os
import re
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
raw_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'raw', 'lawplayer', 'civil_procedure_code')

for name in ['civil_art_2.rsc.json', 'cpc_art_244.rsc.json']:
    with open(os.path.join(raw_dir, name), 'r', encoding='utf-8') as f:
        rsc = f.read()
    
    lines = rsc.split('\n')
    line_dict = {}
    for line in lines:
        m = re.match(r'^([0-9a-f]+):(.*)$', line)
        if m:
            line_dict[m.group(1)] = m.group(2)
            
    print(f"\n=== INSPECTING {name} ===")
    for k, v in line_dict.items():
        if 'surfaceId' in v:
            print(f"Key {k} has surfaceId:")
            print("  ", v)

