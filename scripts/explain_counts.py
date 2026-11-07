import sqlite3
import json

conn = sqlite3.connect("data/legal_hub.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

with open("data/ChLaw.json", "r", encoding="utf-8-sig") as f:
    d = json.load(f)
chlaw_names = set(l.get("LawName", "").strip() for l in d.get("Laws", []))

all_acts = cur.execute("SELECT id, pcode, name, category, status FROM acts").fetchall()
in_chlaw = [a for a in all_acts if a["name"] in chlaw_names]
not_in_chlaw = [a for a in all_acts if a["name"] not in chlaw_names]

print(f"Total acts in DB: {len(all_acts)}")
print(f"Acts matching ChLaw.json (中央法規/法律): {len(in_chlaw)}")
print(f"Acts NOT in ChLaw.json: {len(not_in_chlaw)}")

# Count articles for both groups
in_chlaw_ids = set(a["id"] for a in in_chlaw)
in_chlaw_arts = cur.execute(f"SELECT count(*) FROM articles WHERE act_id IN ({','.join('?' for _ in in_chlaw_ids)})", list(in_chlaw_ids)).fetchone()[0]
print(f"Articles in matching acts: {in_chlaw_arts}")
not_in_chlaw_arts = cur.execute(f"SELECT count(*) FROM articles WHERE act_id NOT IN ({','.join('?' for _ in in_chlaw_ids)})", list(in_chlaw_ids)).fetchone()[0]
print(f"Articles in non-matching acts: {not_in_chlaw_arts}")

# Categories of non-matching acts
from collections import Counter
cat_counter = Counter(a["category"].split(" > ")[0] if a["category"] else "未分類" for a in not_in_chlaw)
print("\nTop 10 categories for non-matching acts:")
for cat, count in cat_counter.most_common(10):
    print(f"  {cat}: {count} acts")

