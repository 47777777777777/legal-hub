import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('C:/Users/harry/.gemini/antigravity-ide/scratch/legal-hub/scripts/raw_bytes.bin', 'rb') as f:
    raw = f.read()

text = raw.decode('utf-8', errors='replace')

rows = re.findall(r'<tr[^>]*>([\s\S]*?)</tr>', text, re.I)
print(f"Total tr rows: {len(rows)}")
for i, r in enumerate(rows):
    if 'tdc2' in r:
        print(f"Row {i} has tdc2!")
        # split by <td
        parts = re.split(r'<td', r, flags=re.I)
        print(f"  parts count: {len(parts)}")
        for j, p in enumerate(parts):
            clean = re.sub(r'<[^>]+>', '', p).strip()
            print(f"    td {j}: {clean[:60]}")

