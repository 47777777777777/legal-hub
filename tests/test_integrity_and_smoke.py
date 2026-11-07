import os
import sys
import subprocess
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def test_data_integrity_guardrail():
    script = os.path.join(BASE_DIR, "scripts", "verify_integrity.py")
    res = subprocess.run([sys.executable, "-X", "utf8", script], capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert res.returncode == 0, f"Integrity check failed:\n{res.stdout}\n{res.stderr}"

def test_smoke_ui_playwright():
    script = os.path.join(BASE_DIR, "scripts", "smoke_ui.py")
    res = subprocess.run([sys.executable, "-X", "utf8", script], capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert res.returncode == 0, f"Smoke UI check failed:\n{res.stdout}\n{res.stderr}"

def test_check_7_paywall_guardrail_negative():
    """
    Prompt 3 Negative Test:
    Inject '在上方解鎖' into article_enrichments, assert verify_integrity.py exits with non-zero code,
    then clean up and assert verify_integrity.py passes.
    """
    import sqlite3
    db_path = os.path.join(BASE_DIR, "data", "legal_hub.db")
    script = os.path.join(BASE_DIR, "scripts", "verify_integrity.py")
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # Insert negative test row
    test_act = "B0010001"
    test_art = "__TEST_PAYWALL_ART__"
    cur.execute("DELETE FROM article_enrichments WHERE article_no = ?", (test_art,))
    cur.execute("""
        INSERT INTO article_enrichments (
            act_id, article_no, summary, source, source_url, fetched_at, article_hash
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (test_act, test_art, "這是測試內容在上方解鎖", "https://lawplayer.com", "https://lawplayer.com/test", "2026-11-02", "testhash"))
    conn.commit()
    conn.close()

    try:
        # Run verify_integrity.py, expect FAILURE
        res = subprocess.run([sys.executable, "-X", "utf8", script], capture_output=True, text=True, encoding="utf-8", errors="replace")
        assert res.returncode != 0, f"Expected verify_integrity.py to FAIL on injected paywall string, but succeeded:\n{res.stdout}"
        assert "forbidden paywall string violation" in res.stdout, f"Expected paywall violation message in stdout:\n{res.stdout}"
    finally:
        # Revert test row
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("DELETE FROM article_enrichments WHERE article_no = ?", (test_art,))
        conn.commit()
        conn.close()

    # Verify that clean state passes
    clean_res = subprocess.run([sys.executable, "-X", "utf8", script], capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert clean_res.returncode == 0, f"Expected clean state to pass verify_integrity.py, but failed:\n{clean_res.stdout}"
