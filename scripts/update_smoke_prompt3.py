import os

smoke_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "smoke_ui.py")

with open(smoke_path, "r", encoding="utf-8") as f:
    text = f.read()

# Replace CPC Art 2 un-enriched check with Art 80 (since Art 2 is now authentic enriched)
old_str = "page.evaluate(\"window.legalHubApp.openStudyDrawer('2')\")"
new_str = "page.evaluate(\"window.legalHubApp.openStudyDrawer('80')\")"

assert old_str in text
text = text.replace(old_str, new_str, 1)

with open(smoke_path, "w", encoding="utf-8") as f:
    f.write(text)

print("Updated smoke_ui.py un-enriched test to Art 80!")

