import gzip
import sys
import re

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

gz_file = "data/raw/lis/gz/A0040012.html.gz"
with gzip.open(gz_file, "rt", encoding="utf-8", errors="ignore") as f:
    html = f.read()

idx = html.find("第十七條")
print("Found 第十七條 at:", idx)
sub = html[idx:idx+3500]
print("Raw HTML snippet for 第十七條:")
print(sub)

