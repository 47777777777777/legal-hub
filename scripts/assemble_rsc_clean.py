import os
import re
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
raw_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'raw', 'lawplayer', 'civil_procedure_code')

for name in ['civil_art_2.body.html', 'cpc_art_244.body.html', 'cpc_art_1.body.html', 'cpc_art_277.body.html']:
    filepath = os.path.join(raw_dir, name)
    with open(filepath, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # In Next.js App Router, each push is self.__next_f.push([1, "..."])
    # The string inside can be parsed using regex or json
    raw_pushes = re.findall(r'self\.__next_f\.push\(\[1,\s*"(.*?)"\]\)', html, re.DOTALL)
    
    # Assemble RSC lines
    stream_chunks = []
    for rp in raw_pushes:
        # replace javascript escape sequences
        chunk = json.loads(f'"{rp}"')
        stream_chunks.append(chunk)
    
    full_rsc = "".join(stream_chunks)
    
    # Also write out clean rsc
    rsc_out = os.path.join(raw_dir, name.replace('.body.html', '.rsc.json'))
    with open(rsc_out, 'w', encoding='utf-8') as out_f:
        out_f.write(full_rsc)
    print(f"Processed {name} -> {len(full_rsc)} chars")

