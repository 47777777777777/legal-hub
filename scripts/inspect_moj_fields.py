import json
import os

for fname in ["data/ChLaw.json", "data/ChOrder.json"]:
    if not os.path.exists(fname):
        print(f"{fname} not found!")
        continue
    with open(fname, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
    laws = data.get("Laws", [])
    print(f"\n=== INSPECTING {fname} (total laws: {len(laws)}) ===")
    all_keys = set()
    for l in laws:
        all_keys.update(l.keys())
    print("All keys across laws:", sorted(list(all_keys)))
    
    # Show two samples
    sample1 = laws[0]
    sample2 = laws[1] if len(laws) > 1 else laws[0]
    
    print("\n--- SAMPLE 1 ---")
    for k in sorted(sample1.keys()):
        val = sample1[k]
        if isinstance(val, list):
            print(f"  {k}: [list with {len(val)} items, first item type={val[0].get('ArticleType') if val else 'None'}]")
        else:
            print(f"  {k}: {repr(val)[:100]}")
            
    print("\n--- SAMPLE 2 ---")
    for k in sorted(sample2.keys()):
        val = sample2[k]
        if isinstance(val, list):
            print(f"  {k}: [list with {len(val)} items]")
        else:
            print(f"  {k}: {repr(val)[:100]}")

