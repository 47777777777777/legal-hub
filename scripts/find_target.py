import os

target = "最高行政法院九十九年"
for root, dirs, files in os.walk("."):
    if ".git" in root or ".pytest_cache" in root or "node_modules" in root:
        continue
    for f in files:
        fp = os.path.join(root, f)
        try:
            with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                content = fh.read()
                if target in content:
                    print(f"Found in: {fp}")
        except Exception:
            pass

