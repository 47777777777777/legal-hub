import sys
import gzip
import os
import hashlib

sys.stdout.reconfigure(encoding='utf-8')

sample_1_path = "data/raw/lis/samples/sample_1.html"
a0030055_path = "data/raw/lis/gz/A0030055.html.gz"

s1_size = os.path.getsize(sample_1_path)
print(f"sample_1.html size: {s1_size} bytes ({s1_size/1024:.2f} KB)")

with open(sample_1_path, 'rb') as f:
    s1_bytes = f.read()
print(f"sample_1.html SHA256: {hashlib.sha256(s1_bytes).hexdigest()}")
print(f"sample_1.html head 200:\n{s1_bytes[:200].decode('utf-8', errors='ignore')}")

with gzip.open(a0030055_path, 'rb') as f:
    a_bytes = f.read()

print(f"\nA0030055.html uncompressed size: {len(a_bytes)} bytes ({len(a_bytes)/1024:.2f} KB)")
print(f"A0030055.html.gz disk size: {os.path.getsize(a0030055_path)} bytes ({os.path.getsize(a0030055_path)/1024:.2f} KB)")
print(f"A0030055.html SHA256: {hashlib.sha256(a_bytes).hexdigest()}")
print(f"A0030055.html head 200:\n{a_bytes[:200].decode('utf-8', errors='ignore')}")

# Check difference between sample_1 and A0030055
print(f"\nAre sample_1 and uncompressed A0030055 identical? {s1_bytes == a_bytes}")
if s1_bytes != a_bytes:
    print(f"Size diff: {len(s1_bytes)} vs {len(a_bytes)} (delta: {len(s1_bytes) - len(a_bytes)} bytes)")

