import re

with open('C:/Users/harry/.gemini/antigravity-ide/scratch/legal-hub/scripts/raw_bytes.bin', 'rb') as f:
    raw = f.read()

# Let's decode raw completely as utf-8
text = raw.decode('utf-8', errors='replace')

rows = re.findall(r'<tr[^>]*>([\s\S]*?)</tr>', text)
for r in rows:
    tds = re.findall(r'<td[^>]*>([\s\S]*?)(?=<td|$)', r)
    if len(tds) >= 5:
        # Check if tdc2 is present
        if 'class=tdc2' in tds[1] or 'class="tdc2"' in tds[1]:
            title = re.sub(r'<[^>]+>', '', tds[1]).strip()
            journal = re.sub(r'<[^>]+>', '', tds[2]).strip()
            author = re.sub(r'<[^>]+>', '', tds[3]).strip()
            pub_date = re.sub(r'<[^>]+>', '', tds[4]).strip()
            
            # Find the link inside tds[1]
            link_match = re.search(r'href=[\'"]?([^\s\'">]+)', tds[1])
            link = link_match.group(1) if link_match else ""
            
            print(f"[{pub_date}] 《{title}》")
            print(f"  作者: {author} | 期刊: {journal}")
            print(f"  連結: {link}")
            print("-" * 60)

