with open(r"C:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub\data\raw\lis\samples\user_apa_128_comp_success.html", "r", encoding="utf-8", errors="ignore") as f:
    html = f.read()

pos = 0
while True:
    idx = html.find("一百二十八", pos)
    if idx == -1:
        break
    snippet = html[max(0, idx - 100): min(len(html), idx + 500)]
    print(f"--- Occurrence at {idx} ---")
    print(repr(snippet[:300]))
    pos = idx + 1

