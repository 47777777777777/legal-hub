import json

with open("data/ChLaw.json", "r", encoding="utf-8-sig") as f:
    d = json.load(f)

laws = d.get("Laws", [])
for idx, law in enumerate(laws):
    name = law.get("LawName")
    if name in ["刑事訴訟法", "行政訴訟法", "著作權法"]:
        print(f"MOJ index {idx}: {name}")
    if "刑" in name and "訴訟" in name:
        print(f"  candidate {idx}: {name}")

