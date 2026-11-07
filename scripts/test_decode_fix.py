import re

with open('C:/Users/harry/.gemini/antigravity-ide/scratch/legal-hub/scripts/ntu_law_review.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Let's see what is inside <td class=tdc2> ... </td>
rows = re.findall(r'<tr[^>]*>([\s\S]*?)</tr>', text)
for r in rows:
    tds = re.findall(r'<td[^>]*>([\s\S]*?)(?=<td|$)', r)
    if len(tds) >= 4:
        # Let's inspect the text
        c2 = re.sub(r'<[^>]+>', '', tds[1]).strip()
        c3 = re.sub(r'<[^>]+>', '', tds[2]).strip()
        c4 = re.sub(r'<[^>]+>', '', tds[3]).strip()
        c5 = re.sub(r'<[^>]+>', '', tds[4]).strip() if len(tds) > 4 else ''
        print(f"Title: {repr(c2)}")
        print(f"Journal: {repr(c3)}")
        print(f"Author: {repr(c4)}")
        print(f"Date: {repr(c5)}")
        # Check if latin1 -> cp950 / big5 fixes it!
        try:
            fixed_c2 = c2.encode('latin1').decode('cp950')
            fixed_c3 = c3.encode('latin1').decode('cp950')
            fixed_c4 = c4.encode('latin1').decode('cp950')
            print(">>> FIXED WITH latin1 -> cp950:")
            print(f"  Title: {fixed_c2}")
            print(f"  Journal: {fixed_c3}")
            print(f"  Author: {fixed_c4}")
        except Exception as e:
            print("latin1 decode error:", e)
        print("-" * 50)

