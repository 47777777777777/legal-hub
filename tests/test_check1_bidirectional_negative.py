"""
tests/test_check1_bidirectional_negative.py

Prompt 4F Section 2-4:
Check 1 雙向負向測試：嚴格隔離正式資料庫！
使用 shutil.copy2 將 legal_hub.db 複製至 temp_negative_test.db，
在暫存資料庫上刪除 A0000005 的前言列，執行 verify_integrity.py --db temp_negative_test.db 斷言失敗。
測試完成後立即刪除暫存檔，並比對正式 legal_hub.db 的 sha256 與 row count 前後 100% 一致。
"""

import os
import sys
import sqlite3
import subprocess
import shutil
import hashlib
from pathlib import Path
import pytest

BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data" / "legal_hub.db"
TEMP_DB_PATH = BASE_DIR / "data" / "temp_negative_test.db"
SCRIPT_PATH = BASE_DIR / "scripts" / "verify_integrity.py"

def get_db_metrics(path: Path):
    with open(path, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    acts_cnt = cur.execute("SELECT count(*) FROM acts").fetchone()[0]
    arts_cnt = cur.execute("SELECT count(*) FROM articles").fetchone()[0]
    foreword_cnt = cur.execute("SELECT count(*) FROM act_forewords").fetchone()[0]
    conn.close()
    return sha, acts_cnt, arts_cnt, foreword_cnt

def test_check1_bidirectional_negative_foreword_isolated():
    # 1. Capture production DB metrics before test
    sha_before, acts_before, arts_before, foreword_before = get_db_metrics(DB_PATH)
    
    # 2. Copy production DB to temp DB
    if TEMP_DB_PATH.exists():
        TEMP_DB_PATH.unlink()
    shutil.copy2(DB_PATH, TEMP_DB_PATH)
    
    try:
        # 3. Corrupt temp DB: delete A0000005 foreword
        conn = sqlite3.connect(TEMP_DB_PATH)
        cur = conn.cursor()
        cur.execute("DELETE FROM act_forewords WHERE pcode = 'A0000005'")
        assert cur.rowcount > 0, "A0000005 foreword must exist in temp DB to delete"
        conn.commit()
        conn.close()
        
        # 4. Run verify_integrity.py on temp DB, MUST FAIL
        res = subprocess.run(
            [sys.executable, "-X", "utf8", str(SCRIPT_PATH), "--db", str(TEMP_DB_PATH)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        assert res.returncode != 0, f"Expected verify_integrity.py to FAIL on temp DB, but got code 0:\n{res.stdout}"
        assert "FAIL: Missing foreword in database for act A0000005" in res.stdout, (
            f"Expected 'FAIL: Missing foreword in database for act A0000005' in output:\n{res.stdout}"
        )
        print("\n[Isolated Negative Test Verified Failure on Temp DB]:\n" + res.stdout)
        
    finally:
        # 5. Clean up temp DB
        if TEMP_DB_PATH.exists():
            TEMP_DB_PATH.unlink()
            
    # 6. Verify production DB is 100% UNTOUCHED
    sha_after, acts_after, arts_after, foreword_after = get_db_metrics(DB_PATH)
    assert sha_before == sha_after, f"Production DB sha256 changed! Before: {sha_before}, After: {sha_after}"
    assert acts_before == acts_after
    assert arts_before == arts_after
    assert foreword_before == foreword_after
    print("\n[Production DB Untouched Assertion]: sha256 and row counts identical before and after test!")
