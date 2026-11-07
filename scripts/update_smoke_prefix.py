with open('scripts/smoke_ui.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('BASE_URL = f"http://127.0.0.1:{PORT}"', 'BASE_URL = os.environ.get("BASE_URL", f"http://127.0.0.1:{PORT}")\nSCREENSHOT_PREFIX = os.environ.get("SCREENSHOT_PREFIX", "local_")')
text = text.replace('"local_cpc_art_2.png"', 'f"{SCREENSHOT_PREFIX}cpc_art_2.png"')
text = text.replace('"local_cpc_art_244.png"', 'f"{SCREENSHOT_PREFIX}cpc_art_244.png"')
text = text.replace('"local_criminal_art_2.png"', 'f"{SCREENSHOT_PREFIX}criminal_art_2.png"')
text = text.replace('"local_unenriched_art.png"', 'f"{SCREENSHOT_PREFIX}unenriched_art.png"')

with open('scripts/smoke_ui.py', 'w', encoding='utf-8') as f:
    f.write(text)
print('Updated smoke_ui.py for remote prefix & BASE_URL')

