import re

with open('C:/Users/harry/.gemini/antigravity-ide/scratch/legal-hub/scripts/pdf_response.html', 'r', encoding='utf-8') as f:
    html = f.read()

print("Title:", re.findall(r'<title>(.*?)</title>', html, re.I))
# Search for iframes, embeds, object, pdf links, or download buttons
print("Iframes:", re.findall(r'<iframe[^>]+src=[\'"]?([^\s\'">]+)', html, re.I))
print("Embeds/Objects:", re.findall(r'<(?:embed|object)[^>]+src=[\'"]?([^\s\'">]+)', html, re.I))
print("Links with pdf/download:", re.findall(r'<a[^>]+href=[\'"]?([^\s\'">]+)[^>]*>([\s\S]*?)</a>', html, re.I)[:10])

for line in html.split('\n'):
    if any(k in line.lower() for k in ['pdf', 'viewer', 'download', 'window.open', 'location.href']):
        print("MATCH:", line.strip()[:150])

