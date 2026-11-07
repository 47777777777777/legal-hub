import sqlite3
import random
import json
import yaml
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "legal_hub.db")
TIERS_PATH = os.path.join(BASE_DIR, "config", "tiers.yaml")
OUT_PATH = os.path.join(BASE_DIR, "tests", "fixtures", "stratified_100.json")

def generate():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    rng = random.Random(42)

    with open(TIERS_PATH, "r", encoding="utf-8") as f:
        tcfg = yaml.safe_load(f)
    tier1_acts = tcfg["tier_1"]["acts"]

    sample_100 = []
    
    # 1. 10 核心法規 (4條 each = 40條)
    for act_id in tier1_acts[:10]:
        cur.execute("SELECT act_id, article_no, content FROM articles WHERE act_id = ? AND status = 'active'", (act_id,))
        arts = cur.fetchall()
        chosen = rng.sample(arts, min(4, len(arts)))
        for c in chosen:
            sample_100.append({
                "type": "core",
                "act_id": c[0],
                "article_no": c[1],
                "content_len": len(c[2])
            })

    # 2. 其他母法 (30 條)
    placeholders = ",".join("?" * len(tier1_acts))
    cur.execute(f"""
        SELECT a.id, art.article_no, art.content 
        FROM acts a 
        JOIN articles art ON a.id = art.act_id 
        WHERE a.id NOT IN ({placeholders}) 
          AND (a.category LIKE '%法律%' OR a.name LIKE '%法' OR a.name LIKE '%條例')
          AND a.category NOT LIKE '%命令%'
          AND art.status = 'active'
    """, tier1_acts)
    other_arts = cur.fetchall()
    chosen_other = rng.sample(other_arts, 30)
    for c in chosen_other:
        sample_100.append({
            "type": "other_law",
            "act_id": c[0],
            "article_no": c[1],
            "content_len": len(c[2])
        })

    # 3. 法規命令 (30 條)
    cur.execute("""
        SELECT a.id, art.article_no, art.content 
        FROM acts a 
        JOIN articles art ON a.id = art.act_id 
        WHERE a.category LIKE '%命令%'
          AND art.status = 'active'
    """)
    order_arts = cur.fetchall()
    chosen_orders = rng.sample(order_arts, 30)
    for c in chosen_orders:
        sample_100.append({
            "type": "order",
            "act_id": c[0],
            "article_no": c[1],
            "content_len": len(c[2])
        })

    conn.close()
    
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(sample_100, f, ensure_ascii=False, indent=2)

    print(f"Generated {len(sample_100)} stratified sample articles into {OUT_PATH}")

if __name__ == "__main__":
    generate()

