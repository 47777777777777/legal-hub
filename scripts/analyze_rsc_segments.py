import os
import re
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
raw_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'raw', 'lawplayer', 'civil_procedure_code')

with open(os.path.join(raw_dir, 'civil_art_2.rsc.json'), 'r', encoding='utf-8') as f:
    rsc = f.read()

# Let's see all lines or segments starting with id:
# RSC lines are like:
# 1e:{"metadata":...}
# 4d:["$", ...]
lines = rsc.split('\n')
print(f"Total lines in RSC: {len(lines)}")

# Let's inspect lines containing keywords
keywords = ['適用習慣之限制', '10503501700', '立法沿革', '白話', '判決']
for kw in keywords:
    print(f"\n=== MATCHES FOR '{kw}' ===")
    matches = [line for line in lines if kw in line]
    print(f"Found {len(matches)} lines")
    for m in matches[:3]:
        # print first 300 chars
        print("  LINE:", m[:400], "...\n")

