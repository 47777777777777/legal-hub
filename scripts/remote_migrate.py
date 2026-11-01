import sqlite3
import os

db_path = "data/legal_hub.db"
conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute("UPDATE articles SET reading_time = NULL WHERE reading_time = '3 分鐘'")
c.execute("UPDATE article_enrichments SET reading_time = NULL WHERE reading_time = '3 分鐘'")
conn.commit()
print("Updated reading_time to NULL for mock '3 分鐘' values")
conn.close()
