import re
import glob
import sys
import hashlib

sys.stdout.reconfigure(encoding="utf-8")

pattern = re.compile(r'\|\|\s*(["\'`])([^"\'`]*[\u4e00-\u9fa5]+[^"\'`]*)\1')
matches = []
for p in glob.glob("static/js/*.js"):
    p_norm = p.replace("\\", "/")
    with open(p, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            for m in pattern.finditer(line):
                line_str = line.strip()
                line_hash = hashlib.sha256(line_str.encode("utf-8")).hexdigest()[:16]
                matches.append({
                    "file": p_norm,
                    "line_no": idx,
                    "value": m.group(2),
                    "line_hash": line_hash,
                    "line": line_str
                })

for item in matches:
    print(f"{item['file']}:{item['line_no']} -> \"{item['value']}\" (hash: {item['line_hash']})\n   {item['line']}")
print(f"Total || Chinese matches: {len(matches)}")
