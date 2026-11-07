import os
import sys
import json
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "legal_hub.db")
OUT_PATH = os.path.join(BASE_DIR, "data", "lis_export.json")

def export_lis():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    def clean_row(d):
        r = dict(d)
        if "raw_path" in r and r["raw_path"]:
            norm = r["raw_path"].replace("\\", "/")
            if "data/raw/" in norm:
                r["raw_path"] = "data/raw/" + norm.split("data/raw/")[1]
        return r

    reasons = [clean_row(r) for r in c.execute("SELECT * FROM article_reasons").fetchall()]
    versions = [clean_row(r) for r in c.execute("SELECT * FROM article_versions").fetchall()]
    comparisons = [clean_row(r) for r in c.execute("SELECT * FROM article_comparison").fetchall()]
    
    data = {
        "article_reasons": reasons,
        "article_versions": versions,
        "article_comparison": comparisons
    }
    
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    print(f"Exported LIS data to {OUT_PATH}:")
    print(f"  article_reasons: {len(reasons)}")
    print(f"  article_versions: {len(versions)}")
    print(f"  article_comparison: {len(comparisons)}")

if __name__ == "__main__":
    export_lis()

