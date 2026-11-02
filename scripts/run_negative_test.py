"""
scripts/run_negative_test.py

Runs negative tests for integrity checks, specifically Check 7:
Injects forbidden paywall string ("在上方解鎖") into article_enrichments,
demonstrating that verify_integrity.py terminates with non-zero exit code.
Then cleanly rolls back the test row and confirms clean exit.
"""
import os
import sys
import sqlite3
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "legal_hub.db")
SCRIPT_PATH = os.path.join(BASE_DIR, "scripts", "verify_integrity.py")

def main():
    print("=== Check 7 Negative Test: Paywall String Guardrail ===")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    test_act = "B0010001"
    test_art = "__NEGATIVE_TEST_PAYWALL_ART__"
    print(f"Injecting test row with '在上方解鎖' into act {test_act}, art {test_art}...")
    cur.execute("""
        INSERT INTO article_enrichments (
            act_id, article_no, summary, source, source_url, fetched_at, article_hash
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (test_act, test_art, "這是付費牆測試內容，在上方解鎖查看完整立法理由", "https://lawplayer.com", "https://lawplayer.com/test", "2026-11-02", "testhash"))
    conn.commit()
    conn.close()

    try:
        print("\n--- Running verify_integrity.py (EXPECTING FAILURE) ---")
        res = subprocess.run([sys.executable, "-X", "utf8", SCRIPT_PATH], capture_output=True, text=True, encoding="utf-8", errors="replace")
        print(f"Exit code: {res.returncode}")
        print("Stdout:\n" + res.stdout)
        if res.returncode != 0 and "forbidden paywall string violation" in res.stdout:
            print(">>> VERIFICATION: Guardrail successfully caught forbidden paywall string! <<<")
        else:
            print(">>> ERROR: Guardrail failed to intercept paywall string! <<<")
            sys.exit(1)
    finally:
        print("\n--- Cleaning up test row ---")
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("DELETE FROM article_enrichments WHERE article_no = ?", (test_art,))
        conn.commit()
        conn.close()
        print("Cleaned up successfully.")

    print("\n--- Running verify_integrity.py on clean database (EXPECTING SUCCESS) ---")
    clean_res = subprocess.run([sys.executable, "-X", "utf8", SCRIPT_PATH], capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(f"Exit code: {clean_res.returncode}")
    assert clean_res.returncode == 0, f"Clean DB failed:\n{clean_res.stdout}"
    print(">>> Negative test fully passed and DB is clean! <<<")

if __name__ == "__main__":
    main()
