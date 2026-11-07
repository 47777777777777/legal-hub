import os
import re
import json

raw_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'raw', 'lawplayer', 'civil_procedure_code')

for name in ['civil_art_2.body.html', 'cpc_art_244.body.html']:
    filepath = os.path.join(raw_dir, name)
    with open(filepath, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # Extract all self.__next_f.push calls
    pushes = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', html)
    print(f"{name}: found {len(pushes)} pushes")
    
    # Let's inspect the pushes and unescape them
    full_stream = ""
    for p in pushes:
        # standard unescape
        try:
            chunk = json.loads(f'"{p}"')
            full_stream += chunk
        except Exception:
            full_stream += p
            
    out_rsc = os.path.join(raw_dir, name.replace('.body.html', '.rsc.txt'))
    with open(out_rsc, 'w', encoding='utf-8') as out_f:
        out_f.write(full_stream)
    print(f"  Saved RSC stream to {out_rsc} ({len(full_stream)} chars)")

