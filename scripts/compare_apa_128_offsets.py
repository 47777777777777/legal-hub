import gzip
import re
from bs4 import BeautifulSoup

# 1. Full act history page
with gzip.open(r"C:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub\data\raw\lis\gz\A0030055.html.gz", "rt", encoding="utf-8", errors="ignore") as f:
    full_html = f.read()

# 2. Comparison page from user's URL
with open(r"C:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub\data\raw\lis\samples\user_apa_128_comp_success.html", "r", encoding="utf-8", errors="ignore") as f:
    comp_html = f.read()

# Find APA 128 (1091230) in full act history
# In A0030055, search for the reason text starting with '一、本項新增'
m_full = re.search(r'一、本項新增。[\s\S]*?(?=</td>|</tr>)', full_html)
full_reason = m_full.group(0).strip() if m_full else ""
full_offset = m_full.start() if m_full else -1

# In comp_html, search for the same
m_comp = re.search(r'一、本項新增。[\s\S]*?(?=</td>|</tr>)', comp_html)
comp_reason = m_comp.group(0).strip() if m_comp else ""
comp_offset = m_comp.start() if m_comp else -1

print("=== Part 2 Item 9 Verification ===")
print(f"(a) Full act history reason length: {len(full_reason)}, offset: {full_offset}")
print(f"(b) Comparison page explanation length: {len(comp_reason)}, offset: {comp_offset}")
print(f"(c) Verbatim identical: {full_reason == comp_reason}")

if full_reason != comp_reason:
    print("Diff:")
    print("  Full reason head:", repr(full_reason[:80]))
    print("  Comp reason head:", repr(comp_reason[:80]))
else:
    print("Both texts are 100% verbatim identical!")
    print("Text head (120 chars):", repr(full_reason[:120]))

