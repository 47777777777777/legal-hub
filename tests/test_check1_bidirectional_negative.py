"""
tests/test_check1_bidirectional_negative.py

Prompt 4D Check 1 Bidirectional Negative Test:
從資料庫刪除臨時條款（A0000005）的前言列 -> verify_integrity.py 必須失敗；還原後必須通過。
"""

import os
import sys
import sqlite3
import subprocess
import pytest
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data" / "legal_hub.db"
SCRIPT_PATH = BASE_DIR / "scripts" / "verify_integrity.py"

def test_check1_bidirectional_negative_foreword():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # 1. Fetch backup of A0000005 foreword
    cur.execute("SELECT * FROM act_forewords WHERE pcode = 'A0000005'")
    row = cur.fetchone()
    assert row is not None, "A0000005 foreword must exist before test starts"
    backup_data = dict(row)
    
    try:
        # 2. Delete A0000005 foreword row
        cur.execute("DELETE FROM act_forewords WHERE pcode = 'A0000005'")
        conn.commit()
        conn.close()
        
        # 3. Run verify_integrity.py, expect FAILURE
        res = subprocess.run(
            [sys.executable, "-X", "utf8", str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        assert res.returncode != 0, f"Expected verify_integrity.py to FAIL on deleted foreword, but got code 0:\n{res.stdout}"
        assert "FAIL: Missing foreword in database for act A0000005" in res.stdout, (
            f"Expected 'FAIL: Missing foreword in database for act A0000005' in output:\n{res.stdout}"
        )
        print("\n[Negative Test Output Verified]:\n" + res.stdout)
        
    finally:
        # 4. Restore A0000005 foreword
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO act_forewords (act_id, pcode, content, content_hash)
            VALUES (?, ?, ?, ?)
        """, (backup_data["act_id"], backup_data["pcode"], backup_data["content"], backup_data["content_hash"]))
        conn.commit()
        conn.close()
        
    # 5. Clean run must pass cleanly
    clean_res = subprocess.run(
        [sys.executable, "-X", "utf8", str(SCRIPT_PATH)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    assert clean_res.returncode == 0, f"Expected clean verify_integrity.py to PASS, but failed:\n{clean_res.stdout}"

