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
    # Find all interp matches: href="/rule/(...)"
    interp_matches = re.findall(r'href=[\"\'](/rule/([a-f0-9]+))[\"\'][^>]*>(.*?)</a>', rsc)
    print(f"Interp matches count: {len(interp_matches)}")
    for url, rid, text in interp_matches:
        # Let's find context around it to get org and date
        pos = rsc.find(rid)
        snippet = rsc[pos:pos+350]
        # extract date
        date_m = re.search(r'(\d{4}-\d{2}-\d{2})', snippet)
        date = date_m.group(1) if date_m else None
        # extract org (e.g. 司法院, 法務部, etc.)
        # snippet usually has "children":"司法院" or similar
        org_m = re.search(r'\"children\":\s*\"([^\"]*(?:院|部|處|局|會|署)[^\"]*)\"', snippet)
        org = org_m.group(1) if org_m else None
        print(f"  ID: {rid} | Ref: {text} | Org: {org} | Date: {date} | URL: {url}")

