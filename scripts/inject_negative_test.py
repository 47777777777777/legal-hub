with open("static/js/app.js", "r", encoding="utf-8") as f:
    text = f.read()

# Inject || "最高法院"
assert 'esc(ins.ref)' in text
text_injected = text.replace('esc(ins.ref)', 'esc(ins.ref || "最高法院")', 1)

with open("static/js/app.js", "w", encoding="utf-8") as f:
    f.write(text_injected)

print("Injected negative test fallback || '最高法院'")

