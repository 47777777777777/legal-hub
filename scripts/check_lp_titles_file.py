import json
with open("data/all_authentic_lp_titles.json", "r", encoding="utf-8") as f:
    d = json.load(f)
print("Keys in all_authentic_lp_titles.json:", list(d.keys()))
for k in d.keys():
    print(f"  {k}: {len(d[k])} items")

