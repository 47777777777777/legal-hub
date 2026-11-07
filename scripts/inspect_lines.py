import os
import re
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
raw_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'raw', 'lawplayer', 'civil_procedure_code')

with open(os.path.join(raw_dir, 'civil_art_2.rsc.json'), 'r', encoding='utf-8') as f:
    rsc = f.read()

lines = rsc.split('\n')
line_dict = {}
for line in lines:
    m = re.match(r'^([0-9a-f]+):(.*)$', line)
    if m:
        line_dict[m.group(1)] = m.group(2)

print(f"Total keyed lines in RSC: {len(line_dict)}")

# Let's inspect line '46' (title)
print("Line 46 (Title):")
print(line_dict.get('46'))

# Let's inspect line '38' (Facts summary / Legislative history)
print("\nLine 38 (Facts/History):")
print(line_dict.get('38'))

# Let's find interpretations in line '4c' or references $L5f, $L60, etc.
for k in ['4c', '5f', '60', '61', '62', '63', '64']:
    if k in line_dict:
        print(f"\nLine {k}:")
        print(line_dict[k][:300])

