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

val_4c = line_dict.get('4c', '')
# write val_4c formatted or inspect sub-elements
with open(os.path.join(raw_dir, 'civil_art_2_tab_4c.txt'), 'w', encoding='utf-8') as f:
    f.write(val_4c)

print(f"Wrote line 4c ({len(val_4c)} chars)")

# Let's search for references $Lxx in 4c
refs = re.findall(r'\$L([0-9a-f]+)', val_4c)
print("References inside 4c:", sorted(list(set(refs))))
for ref in sorted(list(set(refs))):
    if ref in line_dict:
        print(f"--- Ref {ref} ---")
        print(line_dict[ref][:200])

