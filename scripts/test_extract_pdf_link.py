import re

with open('C:/Users/harry/.gemini/antigravity-ide/scratch/legal-hub/scripts/raw_bytes.bin', 'rb') as f:
    text = f.read().decode('utf-8', errors='replace')

parts = re.split(r'<td\s+', text, flags=re.I)
for i, p in enumerate(parts):
    if 'class=tdc2' in p or 'class="tdc2"' in p:
        # title
        title = re.sub(r'<[^>]+>', '', p).strip()
        # Find next tdc9
        pdf_link = None
        for j in range(i+1, min(i+8, len(parts))):
            if 'tdc9' in parts[j]:
                m = re.search(r"MM_openBrWindow\(['\"]([^'\"]+)['\"]", parts[j], re.I)
                if m:
                    pdf_link = m.group(1)
                break
        print(f"Title: {title[:30]}")
        print(f"  PDF Link: {pdf_link}")

