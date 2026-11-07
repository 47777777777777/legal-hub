import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('C:/Users/harry/.gemini/antigravity-ide/scratch/legal-hub/scripts/lawdata_search_result.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

# Strip tags and print non-empty lines
lines = [l.strip() for l in re.sub(r'<script[\s\S]*?</script>', '', text, flags=re.I).split('\n')]
clean_lines = [re.sub(r'<[^>]+>', ' ', l).strip() for l in lines]
clean_lines = [l for l in clean_lines if l and len(l) > 1]

for line in clean_lines[400:500]:
    print(line)
