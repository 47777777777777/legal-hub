with open('C:/Users/harry/.gemini/antigravity-ide/scratch/legal-hub/scripts/raw_bytes.bin', 'rb') as f:
    raw = f.read()

import re
tdc2_matches = re.findall(b'<td class=tdc2>([\\s\\S]*?)(?=<td|$)', raw)
for i, m in enumerate(tdc2_matches[:5]):
    print(f"--- TDC2 #{i} ---")
    print("Raw bytes:", m[:150])
    # Try different decodings
    for enc in ['utf-8', 'cp950', 'big5', 'gbk']:
        try:
            print(f"  {enc}: {m.decode(enc)[:100].strip()}")
        except Exception as e:
            print(f"  {enc} error: {e}")

