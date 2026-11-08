import sqlite3
import gzip
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

conn = sqlite3.connect("data/legal_hub.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

for rid, act, art, date, gz_file in [
    (6818, "a0040012", "17", "0871009", "data/raw/lis/gz/A0040012.html.gz"),
    (6925, "b0000005", "6-3", "1011207", "data/raw/lis/gz/B0000005.html.gz")
]:
    cur.execute("SELECT * FROM article_reasons WHERE id = ?", (rid,))
    row = dict(cur.fetchone())
    reason = row["reason"]

    with gzip.open(gz_file, "rt", encoding="utf-8", errors="ignore") as f:
        raw_html = f.read()

    clean_raw = re.sub(r'\s+', '', re.sub(r'<[^>]+>', '', raw_html))
    clean_reason = re.sub(r'\s+', '', reason)

    print(f"\n=== Row id={rid} ({act} art={art} date={date}) ===")
    print(f"Reason length: {len(reason)}, Clean reason length: {len(clean_reason)}")
    print(f"Clean reason in raw HTML: {clean_reason in clean_raw}")
    if clean_reason not in clean_raw:
        prefix_len = 0
        for i in range(1, len(clean_reason) + 1):
            if clean_reason[:i] in clean_raw:
                prefix_len = i
            else:
                break
        print(f"Matching prefix length: {prefix_len} of {len(clean_reason)}")
        print(f"First mismatch char: reason has: '{clean_reason[prefix_len:prefix_len+30]}'")
        target_sub = clean_reason[max(0, prefix_len-10):prefix_len]
        idx = clean_raw.find(target_sub)
        print(f"Raw around mismatch: '{clean_raw[idx:idx+60]}'")


conn.close()
