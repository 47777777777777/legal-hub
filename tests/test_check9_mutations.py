import os
import sys
import sqlite3
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "legal_hub.db")
VERIFY_SCRIPT = os.path.join(BASE_DIR, "scripts", "verify_integrity.py")

def test_check9_mutation_modify_one_char():
    """Mutation Test 1: Change one character in a reason row; assert Check 9 FAILS."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, reason FROM article_reasons WHERE act_id = 'admin_procedure_act' AND article_no = '1' LIMIT 1")
    row = cur.fetchone()
    assert row is not None
    orig_id, orig_reason = row[0], row[1]
    
    # Mutate 1 character
    mutated_reason = orig_reason[:-1] + ("X" if orig_reason[-1] != "X" else "Y")
    cur.execute("UPDATE article_reasons SET reason = ? WHERE id = ?", (mutated_reason, orig_id))
    conn.commit()
    conn.close()

    try:
        res = subprocess.run([sys.executable, "-X", "utf8", VERIFY_SCRIPT], capture_output=True, text=True, encoding="utf-8", errors="replace")
        assert res.returncode != 0, f"Expected verify_integrity.py to FAIL on 1-char mutation, but got exit code 0:\n{res.stdout}"
        assert "not a verbatim substring of raw file" in res.stdout, f"Expected verbatim violation in stdout:\n{res.stdout}"
        print(">>> Mutation Test 1 (Modify 1 Char) PASSED (successfully rejected by Check 9):")
        for line in res.stdout.splitlines():
            if "not a verbatim substring" in line or "FAIL:" in line:
                print("   ", line)
    finally:
        # Revert
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("UPDATE article_reasons SET reason = ? WHERE id = ?", (orig_reason, orig_id))
        conn.commit()
        conn.close()

def test_check9_mutation_add_fabricated_sentence():
    """Mutation Test 2: Add a fabricated sentence not in raw file; assert Check 9 FAILS."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, reason FROM article_reasons WHERE act_id = 'criminal_code' AND article_no = '10' LIMIT 1")
    row = cur.fetchone()
    assert row is not None
    orig_id, orig_reason = row[0], row[1]
    
    # Add fabricated sentence
    mutated_reason = orig_reason + " 此處新增立法院原始公報未記載之假理由說明文字。"
    cur.execute("UPDATE article_reasons SET reason = ? WHERE id = ?", (mutated_reason, orig_id))
    conn.commit()
    conn.close()

    try:
        res = subprocess.run([sys.executable, "-X", "utf8", VERIFY_SCRIPT], capture_output=True, text=True, encoding="utf-8", errors="replace")
        assert res.returncode != 0, f"Expected verify_integrity.py to FAIL on added fabricated sentence, but got exit code 0:\n{res.stdout}"
        assert "not a verbatim substring of raw file" in res.stdout, f"Expected verbatim violation in stdout:\n{res.stdout}"
        print(">>> Mutation Test 2 (Add Fabricated Sentence) PASSED (successfully rejected by Check 9):")
        for line in res.stdout.splitlines():
            if "not a verbatim substring" in line or "FAIL:" in line:
                print("   ", line)
    finally:
        # Revert
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("UPDATE article_reasons SET reason = ? WHERE id = ?", (orig_reason, orig_id))
        conn.commit()
        conn.close()

if __name__ == "__main__":
    test_check9_mutation_modify_one_char()
    test_check9_mutation_add_fabricated_sentence()
    print("\nAll Check 9 mutation tests passed successfully!")

