with open('C:/Users/harry/.gemini/antigravity-ide/scratch/legal-hub/scripts/ntu_law_review.html', 'rb') as f:
    raw = f.read()

# Let's inspect the exact raw bytes of that td
import re
for enc in ['cp950', 'big5', 'utf-8']:
    try:
        decoded = raw.decode(enc)
        print(f"=== Decoded with {enc} ===")
        for line in decoded.split('\n'):
            if 'tdc1' in line or 'tdc2' in line or 'tdc3' in line or 'tdc4' in line or 'tdc5' in line:
                print(line.strip())
        break
    except Exception as e:
        print(f"Failed {enc}: {e}")

