import sqlite3

conn = sqlite3.connect("data/legal_hub.db")
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM article_enrichments WHERE act_id = 'criminal_code'")
print("Criminal Code enrichments count in SQLite:", cur.fetchone()[0])

cur.execute("SELECT article_no, title FROM articles WHERE act_id = 'criminal_code' AND title != '' LIMIT 10")
print("Articles with subtitles from LawPlayer:")
for r in cur.fetchall():
    print(f"  第 {r[0]} 條：{r[1]}")

