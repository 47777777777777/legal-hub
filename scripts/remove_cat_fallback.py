with open("static/js/app.js", "r", encoding="utf-8") as f:
    s = f.read()

target = '<span class="act-dropdown-cat">${esc(act.category || "全國法規")}</span>'
replacement = '${act.category ? `<span class="act-dropdown-cat">${esc(act.category)}</span>` : ""}'
assert target in s, "Target not found"
s = s.replace(target, replacement)

with open("static/js/app.js", "w", encoding="utf-8") as f:
    f.write(s)
print("Removed 全國法規 fallback successfully")

