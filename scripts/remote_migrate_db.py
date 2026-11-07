import sqlite3

def main():
    conn = sqlite3.connect("/home/ubuntu/legal-hub/data/legal_hub.db")
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(acts)")
    cols = [r[1] for r in cur.fetchall()]
    print("Acts cols:", cols)
    if "foreword" not in cols:
        print("Adding column foreword to acts...")
        cur.execute("ALTER TABLE acts ADD COLUMN foreword TEXT DEFAULT ''")
        conn.commit()
        print("Column foreword added.")
    
    cur.execute("SELECT id, name, foreword FROM acts WHERE id='a0000005'")
    row = cur.fetchone()
    print("a0000005 foreword in DB:", repr(row[2]) if row else None)
    conn.close()

if __name__ == "__main__":
    main()
