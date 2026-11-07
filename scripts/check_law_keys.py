import json

with open("data/ChLaw.json", "r", encoding="utf-8-sig") as f:
    chlaw = json.load(f)

laws = chlaw.get("Laws", [])
sample = laws[0]
print("All keys in a law object:")
for k, v in sample.items():
    if k != "LawArticles":
        print(f"  {k}: {v}")

