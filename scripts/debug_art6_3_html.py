import gzip
import sys
import re

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

gz_file = "data/raw/lis/gz/B0000005.html.gz"
with gzip.open(gz_file, "rt", encoding="utf-8", errors="ignore") as f:
    html = f.read()

matches = re.findall(r'第[^\n<]+條[^\n<]*', html)
print("Article headers found in B0000005:", matches[:10])

idx = html.find("1011207")
print("Found 1011207 at:", idx)
if idx != -1:
    print("Raw HTML snippet for 1011207:")
    print(html[idx-100:idx+1500])

