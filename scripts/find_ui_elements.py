import re

with open('static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

ids = re.findall(r'id="([^"]+)"', text)
matches = [i for i in ids if any(k in i.lower() for k in ['update', 'status', 'modal', 'banner', 'bookmark'])]
print("Matched IDs in index.html:", matches)

with open('static/js/app.js', 'r', encoding='utf-8') as f:
    app_text = f.read()

funcs = [m for m in re.findall(r'function\s+([a-zA-Z0-9_]+)', app_text) if any(k in m.lower() for k in ['update', 'status', 'banner', 'bookmark', 'stale'])]
print("Matched functions in app.js:", funcs)

