import sqlite3
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "legal_hub.db")
CHLAW_PATH = os.path.join(BASE_DIR, "data", "ChLaw.json")

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# 1. Update abandon_note from ChLaw.json
with open(CHLAW_PATH, "r", encoding="utf-8-sig", errors="ignore") as f:
    laws = json.load(f)["Laws"]

updated_notes = 0
for l in laws:
    note = (l.get("LawAbandonNote") or "").strip()
    name = l.get("LawName", "").strip()
    if note and name:
        cur.execute("UPDATE acts SET abandon_note = ? WHERE name = ?", (note, name))
        updated_notes += cur.rowcount

# 2. Reset articles of abolished acts to 'active' (except literal deletions)
cur.execute("""
    UPDATE articles SET status = 'active'
    WHERE act_id IN (SELECT id FROM acts WHERE status = 'abolished')
      AND content NOT LIKE '%（刪除）%' AND content NOT LIKE '%(刪除)%'
""")
restored_articles = cur.rowcount

conn.commit()

# Verify counts
total_acts = cur.execute("SELECT count(*) FROM acts").fetchone()[0]
abolished_acts = cur.execute("SELECT count(*) FROM acts WHERE status = 'abolished'").fetchone()[0]
active_arts = cur.execute("SELECT count(*) FROM articles WHERE status = 'active'").fetchone()[0]
deleted_arts = cur.execute("SELECT count(*) FROM articles WHERE status = 'deleted'").fetchone()[0]

print(f"Updated {updated_notes} acts with abandon_note.")
print(f"Restored {restored_articles} articles to status='active' for abolished acts.")
print(f"DB Overview: {total_acts} acts ({abolished_acts} abolished), {active_arts} active articles, {deleted_arts} deleted articles.")

conn.close()

