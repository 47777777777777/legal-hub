import gzip
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

gz_path = "data/raw/lis/gz/M0060027.html.gz"
with gzip.open(gz_path, "rt", encoding="utf-8", errors="ignore") as f:
    raw_html = f.read()

idx = raw_html.find("漁業法")
print(f"Found '漁業法' at index: {idx}")
if idx != -1:
    print(repr(raw_html[idx-50:idx+200]))
