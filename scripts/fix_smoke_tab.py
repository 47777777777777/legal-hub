with open("scripts/smoke_ui.py", "r", encoding="utf-8") as f:
    text = f.read()

target = "page.click('.drawer-tab-btn[data-tab=\"legislative\"]')"
replacement = "page.click('.drawer-tab-btn[data-tab=\"legislative_history\"]')"
assert target in text
text = text.replace(target, replacement)

with open("scripts/smoke_ui.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Updated smoke_ui.py with data-tab=legislative_history")

