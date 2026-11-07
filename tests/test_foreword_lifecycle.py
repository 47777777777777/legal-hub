"""
tests/test_foreword_lifecycle.py
Tests official LawForeword lifecycle across onboarding, diff, and apply using an isolated DB.
"""

import sqlite3
import pytest
from backend.db import init_database
from backend.updater.onboarding import onboard_single_act
from backend.updater.moj import MojSource

def get_test_db(tmp_path):
    db_file = str(tmp_path / "test.db")
    init_database(db_file)
    conn = sqlite3.connect(db_file)
    return conn

def test_foreword_onboarding_and_lifecycle(tmp_path):
    conn = get_test_db(tmp_path)
    cur = conn.cursor()

    # 1. Onboard act with LawForeword
    law_payload = {
        "LawName": "測試前言法",
        "LawPcode": "T9999999",
        "LawURL": "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=T9999999",
        "LawCategory": "行政 > 內政",
        "LawModifiedDate": "2026-11-07",
        "LawForeword": "茲為測試法規前言生命週期，特制定本法。",
        "LawArticles": [
            {
                "ArticleType": "A",
                "ArticleNo": "第 1 條",
                "ArticleContent": "本法依據測試規則制定之。"
            }
        ]
    }

    ok, msg, act_id = onboard_single_act(law_payload, conn, force_check1_pass=True)
    assert ok is True, f"Onboarding failed: {msg}"
    assert act_id is not None

    # Verify foreword in acts table
    cur.execute("SELECT foreword FROM acts WHERE id = ?", (act_id,))
    act_fw = cur.fetchone()[0]
    assert act_fw == "茲為測試法規前言生命週期，特制定本法。"

    # Verify foreword in act_forewords table
    cur.execute("SELECT content, content_hash FROM act_forewords WHERE act_id = ?", (act_id,))
    fw_row = cur.fetchone()
    assert fw_row is not None
    assert fw_row[0] == "茲為測試法規前言生命週期，特制定本法。"

    # 2. Test MOJ diff detects modified foreword
    updater = MojSource(config={"test_chlaw_file": True})
    
    # Simulate incoming ChLaw update with modified foreword
    modified_payload = dict(law_payload)
    modified_payload["LawForeword"] = "茲修正法規前言第二版內容。"
    modified_payload["LawArticles"] = [
        {
            "ArticleType": "A",
            "ArticleNo": "第 1 條",
            "ArticleContent": "本法依據測試規則制定之。"
        }
    ]

    import tempfile, json
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as tf:
        json.dump({"Laws": [modified_payload]}, tf, ensure_ascii=False)
        temp_raw_path = tf.name

    try:
        diff_res = updater.diff({"raw_path": temp_raw_path}, conn)
        changes = diff_res["changes"]
        fw_change = next((c for c in changes if c["change_type"] == "modify_act_foreword"), None)
        assert fw_change is not None, "Diff must detect modify_act_foreword change"
        assert fw_change["detail"]["new_foreword"] == "茲修正法規前言第二版內容。"

        # 3. Apply the foreword modification
        apply_res = updater.apply(diff_res, conn)
        assert apply_res["applied_changes_count"] > 0

        # Verify updated foreword in acts
        cur.execute("SELECT foreword FROM acts WHERE id = ?", (act_id,))
        assert cur.fetchone()[0] == "茲修正法規前言第二版內容。"

        # Verify updated foreword in act_forewords
        cur.execute("SELECT content FROM act_forewords WHERE act_id = ?", (act_id,))
        assert cur.fetchone()[0] == "茲修正法規前言第二版內容。"

    finally:
        import os
        if os.path.exists(temp_raw_path):
            os.remove(temp_raw_path)

    conn.close()
