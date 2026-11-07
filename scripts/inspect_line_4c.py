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

print("Line 4c content:")
val_4c = line_dict.get('4c', '')
pos = val_4c.find("10503501700")
print(val_4c[pos-250:pos+350])

