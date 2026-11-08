import sqlite3, json, os

conn = sqlite3.connect('legal-hub/data/legal_hub.db')
cur = conn.cursor()

cur.execute('''
CREATE TABLE IF NOT EXISTS source_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    act_id TEXT NOT NULL,
    article_no TEXT NOT NULL,
    status TEXT NOT NULL,
    error_reason TEXT,
    duration_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
''')

with open('legal-hub/data/tier1_lis_payload.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for row in data['reasons']:
    (act_id, article_no, version_date, action_type, reason, source, source_url, 
     fetched_at, raw_path, date_label_raw, date_raw, article_no_at_the_time, source_mode) = row
    
    # Adjust remote raw_path
    if raw_path:
        base_name = os.path.basename(raw_path)
        remote_raw_path = f"/home/ubuntu/legal-hub/data/raw/lis/gz/{base_name}"
    else:
        remote_raw_path = None

    cur.execute('''
        SELECT id FROM article_reasons 
        WHERE act_id = ? AND article_no = ? AND version_date = ?
    ''', (act_id, article_no, version_date))
    existing = cur.fetchone()
    if existing:
        cur.execute('''
            UPDATE article_reasons 
            SET action_type = ?, reason = ?, source = ?, source_url = ?, fetched_at = ?, raw_path = ?,
                date_label_raw = ?, date_raw = ?, article_no_at_the_time = ?, source_mode = ?
            WHERE id = ?
        ''', (action_type, reason, source, source_url, fetched_at, remote_raw_path,
              date_label_raw, date_raw, article_no_at_the_time, source_mode, existing[0]))
    else:
        cur.execute('''
            INSERT INTO article_reasons (
                act_id, article_no, version_date, action_type, reason, source, source_url, fetched_at, 
                raw_path, date_label_raw, date_raw, article_no_at_the_time, source_mode
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (act_id, article_no, version_date, action_type, reason, source, source_url, fetched_at,
              remote_raw_path, date_label_raw, date_raw, article_no_at_the_time, source_mode))

for row in data['attempts']:
    source, act_id, article_no, status, error_reason, duration_ms, created_at = row
    cur.execute('DELETE FROM source_attempts WHERE act_id = ? AND source = ? AND article_no = ?', (act_id, source, article_no))
    cur.execute('''
        INSERT INTO source_attempts (source, act_id, article_no, status, error_reason, duration_ms, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (source, act_id, article_no, status, error_reason, duration_ms, created_at))

conn.commit()
cur.execute("SELECT count(*), count(DISTINCT act_id||'|'||article_no) FROM article_reasons")
cnt, dist = cur.fetchone()
print(f"Remote Ingestion Completed! article_reasons count: {cnt} (distinct articles: {dist})")
conn.close()
