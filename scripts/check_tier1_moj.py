import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

with open("data/ChLaw.json", "r", encoding="utf-8-sig") as f:
    chlaw = json.load(f)

laws = chlaw.get("Laws", [])
print(f"Total MOJ Laws: {len(laws)}")

tier1_names = [
    "中華民國憲法",
    "民法",
    "中華民國刑法",
    "民事訴訟法",
    "刑事訴訟法",
    "行政程序法",
    "行政訴訟法",
    "公司法",
    "勞動基準法",
    "著作權法",
    "個人資料保護法",
    "道路交通管理處罰條例"
]

for name in tier1_names:
    matches = [l for l in laws if l.get("LawName") == name]
    if matches:
        m = matches[0]
        # Check keys in m
        print(f"TIER 1 MATCH: {name} -> PCode={m.get('LawPcode') or m.get('PCode')}, Keys={list(m.keys())[:5]}, Articles={len(m.get('LawArticles', []))}")
    else:
        print(f"TIER 1 MISSING IN MOJ: {name}")
