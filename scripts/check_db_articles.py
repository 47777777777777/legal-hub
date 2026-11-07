import sqlite3
import hashlib
from pathlib import Path

DB_PATH = Path("data/legal_hub.db")

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM articles")
    total = cur.fetchone()[0]
    print(f"Total articles in {DB_PATH}: {total}")
    
    cur.execute("SELECT act_id, COUNT(*) FROM articles WHERE act_id IN ('test_act', 'dummy_act', 't0010002') GROUP BY act_id")
    rows = cur.fetchall()
    print("Test acts found:", rows)
    
    # Calculate sha256
    sha256 = hashlib.sha256(DB_PATH.read_bytes()).hexdigest()
    print(f"SHA256 of {DB_PATH}: {sha256}")
    
    # Check all table counts
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    print("\nTable Row Counts:")
    for t in tables:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        cnt = cur.fetchone()[0]
        print(f"  {t}: {cnt}")
    conn.close()

if __name__ == "__main__":
    main()
