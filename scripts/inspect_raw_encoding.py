with open('C:/Users/harry/.gemini/antigravity-ide/scratch/legal-hub/scripts/raw_bytes.bin', 'rb') as f:
    raw = f.read()

# Search for META charset
import re
print("Meta tags in raw:", re.findall(b'<meta[^>]+>', raw, re.I))

# Let's decode with errors='replace' using cp950 and print a slice
text_cp950 = raw.decode('cp950', errors='replace')
for line in text_cp950.split('\n'):
    if 'tdc2' in line or 'tdc3' in line or 'tdc4' in line:
        print(line.strip())
