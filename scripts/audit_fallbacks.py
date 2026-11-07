import re
import glob
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Matches || "..." or || '...' containing Chinese characters
pattern_or = re.compile(r'\|\|\s*(["\'`][^"\'`]*[\u4e00-\u9fa5]+[^"\'`]*["\'`])')
# Matches ? "..." : or ? '...' : containing Chinese characters
pattern_ternary = re.compile(r'\?\s*(["\'`][^"\'`]*[\u4e00-\u9fa5]+[^"\'`]*["\'`])\s*:')
# Matches : "..." containing Chinese characters in ternary
pattern_ternary_else = re.compile(r':\s*(["\'`][^"\'`]*[\u4e00-\u9fa5]+[^"\'`]*["\'`])')

results = []

for fpath in glob.glob('static/js/*.js'):
    with open(fpath, 'r', encoding='utf-8') as f:
        for lineno, line in enumerate(f, 1):
            m_or = pattern_or.findall(line)
            m_t1 = pattern_ternary.findall(line)
            m_t2 = pattern_ternary_else.findall(line)
            if m_or or m_t1 or m_t2:
                results.append((fpath, lineno, line.strip(), m_or, m_t1, m_t2))

print(f"Total lines with Chinese fallbacks/ternary: {len(results)}")
for fpath, lineno, line, m_or, m_t1, m_t2 in results:
    print(f"{fpath}:{lineno}")
    print(f"   CODE: {line}")
    if m_or:
        print(f"   || MATCHES: {m_or}")
    if m_t1 or m_t2:
        print(f"   ?: MATCHES: {m_t1 + m_t2}")
    print()
