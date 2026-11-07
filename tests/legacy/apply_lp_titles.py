import sqlite3
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(BASE_DIR, 'data', 'legal_hub.db')
json_path = os.path.join(BASE_DIR, 'data', 'all_authentic_lp_titles.json')

if not os.path.exists(json_path):
    print(f"Error: {json_path} not found!")
    sys.exit(1)

with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Ensure acts name is '民法'
cur.execute("UPDATE acts SET name = '民法' WHERE id = 'civil_code'")

total_updated = 0
for act_id, titles_map in data.items():
    act_count = 0
    for art_no, title in titles_map.items():
        cur.execute("UPDATE articles SET title = ? WHERE act_id = ? AND article_no = ?", (title, act_id, art_no))
        if title:
            act_count += 1
    print(f"Act {act_id}: updated {act_count} titles")
    total_updated += act_count

conn.commit()
conn.close()
print(f"SUCCESS: applied {total_updated} titles to {db_path}!")

