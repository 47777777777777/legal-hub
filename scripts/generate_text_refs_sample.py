import sqlite3
import csv
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.citations import resolve_citations, DB_PATH

def generate():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # 選擇具有法條引用的代表性法規條文
    cur.execute("SELECT act_id, article_no, content FROM articles WHERE content LIKE '%條%' LIMIT 1000")
    rows = cur.fetchall()
    conn.close()

    os.makedirs("reports", exist_ok=True)
    samples = []
    for act_id, art_no, content in rows:
        cits = resolve_citations(content, host_act_id=act_id, db_path=str(DB_PATH))
        for c in cits:
            samples.append({
                "act_id": act_id,
                "article_no": art_no,
                "ref_text": c["ref_text"],
                "ref_type": c["ref_type"],
                "ref_act_id": c["ref_act_id"],
                "ref_act_name": c["ref_act_name"],
                "ref_article_no": c["ref_article_no"]
            })
            if len(samples) >= 50:
                break
        if len(samples) >= 50:
            break

    out_path = Path("reports") / "text_refs_sample_50.csv"
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "act_id", "article_no", "ref_text", "ref_type", "ref_act_id", "ref_act_name", "ref_article_no"
        ])
        writer.writeheader()
        writer.writerows(samples)
    print(f"Generated {out_path} with {len(samples)} rows.")

if __name__ == "__main__":
    generate()
