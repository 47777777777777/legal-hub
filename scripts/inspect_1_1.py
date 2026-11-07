import os
import sys
import glob
import hashlib
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIS_DIR = os.path.join(BASE_DIR, "data", "raw", "lis")
DB_PATH = os.path.join(BASE_DIR, "data", "legal_hub.db")

print("=== 1-1. (1) data/raw/lis/ 所有行政程序法相關檔案清單 ===")
files = sorted(glob.glob(os.path.join(LIS_DIR, "**", "*"), recursive=True))
apa_files = []
for p in files:
    if os.path.isfile(p):
        name = os.path.basename(p)
        rel = os.path.relpath(p, BASE_DIR).replace("\\", "/")
        if "comp" in name or "apa" in name or "sample" in name or "lglawkm" in name:
            with open(p, "rb") as f:
                b = f.read()
            h = hashlib.sha256(b).hexdigest()
            apa_files.append((rel, len(b), h, p))
            print(f"File: {rel:50s} Size: {len(b):8d} bytes  SHA256: {h}")

print("\n=== 1-1. (2) grep -c 三個關鍵字計數 ===")
terms = ["本項新增", "最高行政法院九十九年", "爰增訂第二項規定，明定新證據之定義與適用範圍"]
for rel, sz, h, p in apa_files:
    try:
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        content = ""
    counts = [content.count(t) for t in terms]
    print(f"[{os.path.basename(p)}] '本項新增': {counts[0]}, '最高行政法院九十九年': {counts[1]}, '爰增訂第二項規定...': {counts[2]}")

print("\n=== 1-1. (3) DB 中第 128 條所有版本的列 (article_reasons & article_comparison) ===")
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("--- article_reasons (Art 128) ---")
reasons = cur.execute("""
    SELECT act_id, article_no, version_date, date_label_raw, date_raw, reason, source_url, raw_path
    FROM article_reasons
    WHERE article_no = '128' OR article_no = '第 128 條'
""").fetchall()
for r in reasons:
    print(f"act_id: {r['act_id']}, article_no: {r['article_no']}, version_date: {r['version_date']}, date_label_raw: {r['date_label_raw']}, date_raw: {r['date_raw']}, raw_path: {r['raw_path']}")
    print(f"reason:\n{r['reason']}")
    print("-" * 50)

print("\n--- article_comparison (Art 128) ---")
comps = cur.execute("""
    SELECT act_id, article_no, new_version_date, old_version_date, date_label_raw, date_raw, col_headers_json, cells_json, reason, source_url, raw_path
    FROM article_comparison
    WHERE article_no = '128' OR article_no = '第 128 條'
""").fetchall()
for r in comps:
    print(f"act_id: {r['act_id']}, article_no: {r['article_no']}, new_version: {r['new_version_date']}, old_version: {r['old_version_date']}, date_label_raw: {r['date_label_raw']}, date_raw: {r['date_raw']}")
    print(f"col_headers_json: {r['col_headers_json']}")
    print(f"cells_json: {r['cells_json']}")
    print(f"reason:\n{r['reason']}")
    print("-" * 50)

print("\n=== 1-1. (3b) 位元組位置 (Offset) 與前後各 200 字原始 HTML ===")
target_text = "一、本項新增。"
for rel, sz, h, p in apa_files:
    try:
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            c = f.read()
    except Exception:
        continue
    pos = c.find(target_text)
    if pos != -1:
        with open(p, "rb") as f:
            raw_bytes = f.read()
        byte_offset = raw_bytes.find(target_text.encode("utf-8"))
        print(f"\nFound in {rel}:")
        print(f"  Character offset: {pos}, UTF-8 byte offset: {byte_offset}")
        start_char = max(0, pos - 200)
        end_char = min(len(c), pos + len(target_text) + 200)
        print("--- Preceding + Succeeding 200 chars Raw HTML snippet ---")
        print(c[start_char:end_char])
        print("---------------------------------------------------------")

print("\n=== 1-1. (4) 原始 HTML 中日期出現位置的原始字串 (含標籤文字) ===")
for rel, sz, h, p in apa_files:
    try:
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            c = f.read()
    except Exception:
        continue
    for dt in ["1091230", "1100120"]:
        idx = 0
        while True:
            pos = c.find(dt, idx)
            if pos == -1:
                break
            snippet = c[max(0, pos - 60):min(len(c), pos + 80)].replace("\r", "").replace("\n", " ")
            print(f"In {os.path.basename(p)} at offset {pos}: ... {snippet} ...")
            idx = pos + len(dt)
