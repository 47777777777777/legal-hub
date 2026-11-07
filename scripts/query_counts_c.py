import sqlite3

conn = sqlite3.connect("data/legal_hub.db")
cur = conn.cursor()

print("--- Query 1 ---")
row1 = cur.execute("SELECT count(*), count(DISTINCT act_id), count(DISTINCT act_id || '|' || article_no) FROM articles").fetchone()
print(f"count(*): {row1[0]}, count(DISTINCT act_id): {row1[1]}, count(DISTINCT act_id || '|' || article_no): {row1[2]}")

print("\n--- Query 2 ---")
rows2 = cur.execute("SELECT status, count(*) FROM acts GROUP BY status").fetchall()
for r in rows2:
    print(f"status: '{r[0]}', count: {r[1]}")

print("\n--- Query 3 ---")
rows3 = cur.execute("SELECT a.status, count(*) FROM articles ar JOIN acts a ON ar.act_id = a.id GROUP BY a.status").fetchall()
for r in rows3:
    print(f"acts.status: '{r[0]}', articles count: {r[1]}")

print("\n--- Articles breakdown by act category ---")
rows4 = cur.execute("""
    SELECT 
        CASE 
            WHEN a.category LIKE '%廢止法規%' THEN '廢止法規'
            WHEN a.category LIKE '%行政%' THEN '行政類'
            WHEN a.category LIKE '%司法%' THEN '司法類'
            ELSE '其他類'
        END as cat_group,
        count(*) 
    FROM articles ar 
    JOIN acts a ON ar.act_id = a.id 
    GROUP BY cat_group
""").fetchall()
for r in rows4:
    print(r)

