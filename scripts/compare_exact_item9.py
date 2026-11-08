import gzip
import re
import os

comp_path = r"C:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub\data\raw\lis\comparisons\comp_1091230.html"
gz_path = r"C:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub\data\raw\lis\gz\A0030055.html.gz"

with open(comp_path, "r", encoding="utf-8", errors="ignore") as f:
    comp_html = f.read()

with gzip.open(gz_path, "rt", encoding="utf-8", errors="ignore") as f:
    full_html = f.read()

# 1. Full act history page reason for APA 128 (1091230)
# Look for '一、本項新增'
m_full = re.search(r'一、本項新增。[\s\S]*?(?=</td>|</tr>)', full_html)
full_reason = m_full.group(0).strip() if m_full else ""
full_offset = m_full.start() if m_full else -1

# 2. Comparison page explanation for APA 128 (1091230)
m_comp = re.search(r'一、本項新增。[\s\S]*?(?=</td>|</tr>)', comp_html)
comp_reason = m_comp.group(0).strip() if m_comp else ""
comp_offset = m_comp.start() if m_comp else -1

# Clean up HTML tags (<br>, \r, whitespace) to compare pure legal text
clean_full = re.sub(r'<[^>]+>', '\n', full_reason)
clean_full = '\n'.join(line.strip() for line in clean_full.splitlines() if line.strip())

clean_comp = re.sub(r'<[^>]+>', '\n', comp_reason)
clean_comp = '\n'.join(line.strip() for line in clean_comp.splitlines() if line.strip())

print("=== Part 2 Item 9 Exact Comparison ===")
print(f"(a) Full act history offset: {full_offset}, length: {len(full_reason)} chars")
print(f"(b) Comparison page offset: {comp_offset}, length: {len(comp_reason)} chars")
print(f"(c) Verbatim text identical: {clean_full == clean_comp}")
print("\n--- (a) Full History Reason (first 100 chars) ---")
print(clean_full[:100].encode('ascii', 'backslashreplace').decode('ascii'))
print("\n--- (b) Comparison Page Explanation (first 100 chars) ---")
print(clean_comp[:100].encode('ascii', 'backslashreplace').decode('ascii'))

