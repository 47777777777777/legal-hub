import sqlite3
import gzip
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

conn = sqlite3.connect("data/legal_hub.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT ar.*, a.name as act_name FROM article_reasons ar JOIN acts a ON ar.act_id = a.id WHERE ar.id = 31981")
row = dict(cur.fetchone())
conn.close()

print(f"Law: {row['act_name']} ({row['act_id']}) Art {row['article_no']} ({row['version_date']})")
print("Stored Reason:\n", repr(row["reason"]))

gz_path = "data/raw/lis/gz/M0060027.html.gz"
with gzip.open(gz_path, "rt", encoding="utf-8", errors="ignore") as f:
    raw_html = f.read()

import html as html_lib
clean_raw = re.sub(r'\s+', '', html_lib.unescape(re.sub(r'<[^>]+>', '', raw_html)))
clean_reason = re.sub(r'\s+', '', html_lib.unescape(row["reason"]))

print(f"\nClean reason len: {len(clean_reason)}")
print(f"In raw: {clean_reason in clean_raw}")

if clean_reason not in clean_raw:
    prefix_len = 0
    for i in range(1, len(clean_reason) + 1):
        if clean_reason[:i] in clean_raw:
            prefix_len = i
        else:
            break
    print(f"Matching prefix length: {prefix_len} of {len(clean_reason)}")
    print(f"First mismatch in reason: '{clean_reason[prefix_len:prefix_len+40]}'")
    target_sub = clean_reason[max(0, prefix_len-10):prefix_len]
    idx = clean_raw.find(target_sub)
    print(f"Raw around mismatch: '{clean_raw[idx:idx+60]}'")

