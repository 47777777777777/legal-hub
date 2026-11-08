import sqlite3

conn = sqlite3.connect("data/legal_hub.db")
cur = conn.cursor()
cur.execute("SELECT COUNT(DISTINCT act_id), COUNT(1) FROM article_reasons")
print("article_reasons:", cur.fetchone())
cur.execute("SELECT COUNT(DISTINCT act_id), COUNT(1) FROM article_versions")
print("article_versions:", cur.fetchone())
cur.execute("SELECT COUNT(1) FROM source_attempts WHERE source='lis'")
print("source_attempts:", cur.fetchone())

