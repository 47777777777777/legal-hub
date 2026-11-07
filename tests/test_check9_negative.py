import os
import sqlite3
import pytest
from scripts.verify_integrity import check_lis_data_authenticity, DB_FILE


def test_check_9_detects_fake_lis_reason():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Insert a fake reason row that is NOT in raw HTML
    cur.execute("""
        INSERT INTO article_reasons (act_id, article_no, version_date, action_type, reason, source, raw_path)
        VALUES ('admin_procedure_act', '9999', '1091230', '修正', '這是一條由AI自動生成的假立法理由，在立法院系統原始HTML並不存在。', '立法院法律系統', 'data/raw/lis/samples/sample_1.html')
    """)
    conn.commit()
    
    try:
        # Check 9 must detect this authenticity violation and return False
        result = check_lis_data_authenticity(conn)
        assert result is False, "Check 9 should have detected fake reason and returned False"
    finally:
        # Clean up
        cur.execute("DELETE FROM article_reasons WHERE act_id='admin_procedure_act' AND article_no='9999'")
        conn.commit()
        conn.close()


def test_check_9_detects_forbidden_paywall_term():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Insert a reason containing forbidden term '解鎖'
    cur.execute("""
        INSERT INTO article_reasons (act_id, article_no, version_date, action_type, reason, source, raw_path)
        VALUES ('admin_procedure_act', '9998', '1091230', '修正', '立法院法律系統理由全文在上方解鎖', '立法院法律系統', 'data/raw/lis/samples/sample_1.html')
    """)
    conn.commit()
    
    try:
        result = check_lis_data_authenticity(conn)
        assert result is False, "Check 9 should have detected forbidden paywall term and returned False"
    finally:
        cur.execute("DELETE FROM article_reasons WHERE act_id='admin_procedure_act' AND article_no='9998'")
        conn.commit()
        conn.close()

