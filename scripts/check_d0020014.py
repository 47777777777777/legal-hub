import sqlite3
import json
import hashlib

conn = sqlite3.connect("data/legal_hub.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

act = cur.execute("SELECT id, name, pcode FROM acts WHERE id = 'd0020014'").fetchone()
print("Act d0020014 in DB:", dict(act))

# Check articles of d0020014 in DB
db_arts = cur.execute("SELECT article_no, content FROM articles WHERE act_id = 'd0020014' LIMIT 3").fetchall()
for a in db_arts:
    print(f"DB Art {a['article_no']}: len={len(a['content'])}, repr={repr(a['content'][:50])}")

# Check articles of d0020014 in ChLaw.json
with open("data/ChLaw.json", "r", encoding="utf-8-sig") as f:
    d = json.load(f)

for law in d.get("Laws", []):
    if law.get("LawName") == act["name"] or "d0020014" in law.get("LawURL", ""):
        print("Found in ChLaw.json:", law.get("LawName"), law.get("LawURL"))
        for a in law.get("LawArticles", [])[:3]:
            no = a.get("ArticleNo", "")
            content = a.get("ArticleContent", "").strip()
            print(f"ChLaw Art {no}: len={len(content)}, repr={repr(content[:50])}")
        break

