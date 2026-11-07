"""
tests/test_updater_simulation.py

Comprehensive simulation tests covering all 11 required scenarios:
(a) 修正一條 (modify an article)
(b) 新增一條造成條號移位 (add an article causing article number shifts)
(c) 刪除一條 (delete an article -> soft delete status='deleted')
(d) 廢止一部法 (abolish an act -> status='abolished', LawAbandonNote stored)
(e) 新增一部法 (add a new act)
(f) 來源格式改版 (canary failure aborts run and leaves DB intact)
(g) 異常量保護觸發 (anomaly protection aborts >3% total or >50% act changes)
(h) apply 後 verify 失敗回滾 (post-write verification failure rolls back transaction)
(i) 連續執行兩次 (idempotence: 2nd run reports 'no_change', DB row count & search count unchanged)
(j) stale 標記與重抓佇列 (content change marks stale=1 and queues in pending_lis)
(k) pending_lis 8 週逾期處理 (pending_lis exceeds 8 retries -> status='expired_8_weeks')
"""

import os
import json
import shutil
import sqlite3
import pytest
import datetime
from pathlib import Path

from backend.db import init_database
from backend.updater.base import check_anomaly, backup_database
from backend.updater.runner import execute_update_run
from backend.updater.moj import MojSource
from backend.updater.lis import LisSource
from backend.updater.lawplayer import LawplayerSource

FIXTURES_DIR = Path(__file__).parent / "fixtures"
FIXTURES_DIR.mkdir(parents=True, exist_ok=True)


@pytest.fixture
def temp_db(tmp_path):
    """Creates a temporary isolated SQLite database with migrations applied."""
    db_file = tmp_path / "test_updater.db"
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    
    # Run migrations on temp db
    import backend.db
    orig_db_file = backend.db.DB_FILE
    backend.db.DB_FILE = str(db_file)
    backend.db.init_database(str(db_file))
    backend.db.DB_FILE = orig_db_file
    
    # Seed baseline Act & Articles for testing
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO acts (id, name, category, last_modified, status)
        VALUES ('test_act', '測試法規', '民事目', '2026-01-01', 'active')
    """)
    cur.execute("""
        INSERT INTO acts (id, name, category, last_modified, status)
        VALUES ('dummy_act', '背景法規', '其他', '2026-01-01', 'active')
    """)
    cur.execute("""
        INSERT INTO articles (act_id, article_no, content, status, stale)
        VALUES 
            ('test_act', '1', '第一條原始條文內容。', 'active', 0),
            ('test_act', '2', '第二條原始條文內容。', 'active', 0),
            ('test_act', '3', '第三條原始條文內容。', 'active', 0)
    """)
    for i in range(1, 101):
        cur.execute("""
            INSERT INTO articles (act_id, article_no, content, status, stale)
            VALUES ('dummy_act', ?, '背景法規條文內容。', 'active', 0)
        """, (str(i),))
    cur.execute("""
        INSERT INTO article_enrichments (act_id, article_no, summary, source, source_url, fetched_at)
        VALUES ('test_act', '1', '第一條原始解析', '法律人', 'https://example.com/1', '2026-01-01')
    """)
    conn.commit()
    conn.close()
    
    return str(db_file)


def create_chlaw_fixture(path: Path, laws: list):
    """Write mock ChLaw fixture with UTF-8 BOM."""
    data = {"Laws": laws}
    with open(path, "w", encoding="utf-8-sig") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# =====================================================================
# (a) 修正一條
# =====================================================================
def test_case_a_modify_article(temp_db, tmp_path):
    fix_path = FIXTURES_DIR / "test_chlaw_modify_a.json"
    laws = [{
        "LawName": "測試法規",
        "LawURL": "https://example.com/test_act",
        "LawModifiedDate": "2026-11-01",
        "LawArticles": [
            {"ArticleType": "A", "ArticleNo": "第 1 條", "ArticleContent": "第一條已修訂之最新條文內容。"},
            {"ArticleType": "A", "ArticleNo": "第 2 條", "ArticleContent": "第二條原始條文內容。"},
            {"ArticleType": "A", "ArticleNo": "第 3 條", "ArticleContent": "第三條原始條文內容。"}
        ]
    }]
    create_chlaw_fixture(fix_path, laws)
    
    src = MojSource({"test_chlaw_file": str(fix_path)})
    conn = sqlite3.connect(temp_db)
    conn.row_factory = sqlite3.Row
    
    res = execute_update_run(src, apply=True, mode="test", conn=conn)
    assert res["status"] == "success"
    
    cur = conn.cursor()
    art1 = cur.execute("SELECT content, stale FROM articles WHERE act_id = 'test_act' AND article_no = '1'").fetchone()
    assert art1[0] == "第一條已修訂之最新條文內容。"
    assert art1[1] == 1  # Marked stale
    
    # Assert article_revisions recorded old content
    rev = cur.execute("SELECT old_content, new_content, change_type FROM article_revisions WHERE act_id = 'test_act' AND article_no = '1'").fetchone()
    assert rev is not None
    assert rev[0] == "第一條原始條文內容。"
    assert rev[1] == "第一條已修訂之最新條文內容。"
    assert rev[2] == "modify_article"
    conn.close()


# =====================================================================
# (b) 新增一條造成條號移位
# =====================================================================
def test_case_b_add_shift_article(temp_db):
    fix_path = FIXTURES_DIR / "test_chlaw_shift_b.json"
    laws = [{
        "LawName": "測試法規",
        "LawURL": "https://example.com/test_act",
        "LawModifiedDate": "2026-11-02",
        "LawArticles": [
            {"ArticleType": "A", "ArticleNo": "第 1 條", "ArticleContent": "第一條原始條文內容。"},
            {"ArticleType": "A", "ArticleNo": "第 1-1 條", "ArticleContent": "增訂之第一條之一。"},
            {"ArticleType": "A", "ArticleNo": "第 2 條", "ArticleContent": "第二條原始條文內容。"},
            {"ArticleType": "A", "ArticleNo": "第 3 條", "ArticleContent": "第三條原始條文內容。"}
        ]
    }]
    create_chlaw_fixture(fix_path, laws)
    
    src = MojSource({"test_chlaw_file": str(fix_path)})
    conn = sqlite3.connect(temp_db)
    res = execute_update_run(src, apply=True, mode="test", conn=conn)
    assert res["status"] == "success"
    
    cur = conn.cursor()
    cnt = cur.execute("SELECT count(*) FROM articles WHERE act_id = 'test_act'").fetchone()[0]
    assert cnt == 4
    new_art = cur.execute("SELECT content FROM articles WHERE act_id = 'test_act' AND article_no = '1-1'").fetchone()
    assert new_art[0] == "增訂之第一條之一。"
    conn.close()


# =====================================================================
# (c) 刪除一條 (Soft Delete status='deleted')
# =====================================================================
def test_case_c_delete_article(temp_db):
    fix_path = FIXTURES_DIR / "test_chlaw_delete_c.json"
    laws = [{
        "LawName": "測試法規",
        "LawURL": "https://example.com/test_act",
        "LawModifiedDate": "2026-11-03",
        "LawArticles": [
            {"ArticleType": "A", "ArticleNo": "第 1 條", "ArticleContent": "第一條原始條文內容。"},
            {"ArticleType": "A", "ArticleNo": "第 2 條", "ArticleContent": "第二條原始條文內容。"}
            # Art 3 removed
        ]
    }]
    create_chlaw_fixture(fix_path, laws)
    
    src = MojSource({"test_chlaw_file": str(fix_path)})
    conn = sqlite3.connect(temp_db)
    res = execute_update_run(src, apply=True, mode="test", conn=conn)
    assert res["status"] == "success"
    
    cur = conn.cursor()
    # Physical row not deleted, marked status='deleted'
    art3 = cur.execute("SELECT status FROM articles WHERE act_id = 'test_act' AND article_no = '3'").fetchone()
    assert art3 is not None
    assert art3[0] == "deleted"
    
    # Assert revision recorded
    rev = cur.execute("SELECT change_type FROM article_revisions WHERE act_id = 'test_act' AND article_no = '3'").fetchone()
    assert rev[0] == "delete_article"
    conn.close()


# =====================================================================
# (d) 廢止一部法
# =====================================================================
def test_case_d_abolish_act(temp_db):
    fix_path = FIXTURES_DIR / "test_chlaw_abolish_d.json"
    laws = [{
        "LawName": "測試法規",
        "LawURL": "https://example.com/test_act",
        "LawModifiedDate": "2026-11-04",
        "LawAbandonNote": "中華民國115年11月4日廢止",
        "LawArticles": []
    }]
    create_chlaw_fixture(fix_path, laws)
    
    src = MojSource({"test_chlaw_file": str(fix_path)})
    conn = sqlite3.connect(temp_db)
    res = execute_update_run(src, apply=True, mode="test", conn=conn)
    assert res["status"] == "success"
    
    cur = conn.cursor()
    act = cur.execute("SELECT status, abandon_note FROM acts WHERE id = 'test_act'").fetchone()
    assert act[0] == "abolished"
    assert "115年11月4日廢止" in act[1]
    conn.close()


# =====================================================================
# (e) 新增一部法
# =====================================================================
def test_case_e_add_act(temp_db):
    fix_path = FIXTURES_DIR / "test_chlaw_add_e.json"
    laws = [
        {
            "LawName": "測試法規",
            "LawURL": "https://example.com/test_act",
            "LawModifiedDate": "2026-01-01",
            "LawArticles": [
                {"ArticleType": "A", "ArticleNo": "第 1 條", "ArticleContent": "第一條原始條文內容。"},
                {"ArticleType": "A", "ArticleNo": "第 2 條", "ArticleContent": "第二條原始條文內容。"},
                {"ArticleType": "A", "ArticleNo": "第 3 條", "ArticleContent": "第三條原始條文內容。"}
            ]
        },
        {
            "LawName": "全新制定法規",
            "LawURL": "https://example.com/PCode=NEW001",
            "LawModifiedDate": "2026-11-05",
            "LawCategory": "行政目",
            "LawArticles": [
                {"ArticleType": "A", "ArticleNo": "第 1 條", "ArticleContent": "全新法規第一條。"}
            ]
        }
    ]
    create_chlaw_fixture(fix_path, laws)
    
    src = MojSource({"test_chlaw_file": str(fix_path)})
    conn = sqlite3.connect(temp_db)
    res = execute_update_run(src, apply=True, mode="test", conn=conn)
    assert res["status"] == "success"
    
    cur = conn.cursor()
    new_act = cur.execute("SELECT id, name, status FROM acts WHERE name = '全新制定法規'").fetchone()
    assert new_act is not None
    assert new_act[1] == "全新制定法規"
    assert new_act[2] == "active"
    
    new_art = cur.execute("SELECT content FROM articles WHERE act_id = ? AND article_no = '1'", (new_act[0],)).fetchone()
    assert new_art[0] == "全新法規第一條。"
    conn.close()


# =====================================================================
# (f) 來源格式改版 (Canary failure aborts and DB stays untouched)
# =====================================================================
def test_case_f_canary_failure(temp_db):
    fix_path = FIXTURES_DIR / "test_chlaw_malformed_f.json"
    # Malformed file missing required Laws array structure
    with open(fix_path, "w", encoding="utf-8") as f:
        f.write('{"Corrupted": []}')
        
    src = MojSource({"test_chlaw_file": str(fix_path)})
    # Override canary to test corrupt source detection
    src.run_canary = lambda: (False, "Simulated upstream schema break in canary.")
    
    conn = sqlite3.connect(temp_db)
    res = execute_update_run(src, apply=True, mode="test", conn=conn)
    assert res["status"] == "canary_failed"
    assert "Canary regression check failed" in res["error"]
    
    # Assert database state remains strictly untouched
    cur = conn.cursor()
    cnt = cur.execute("SELECT count(*) FROM articles WHERE act_id = 'test_act'").fetchone()[0]
    assert cnt == 3
    conn.close()


# =====================================================================
# (g) 異常量保護觸發 (Anomaly volume protection aborts)
# =====================================================================
def test_case_g_anomaly_protection(temp_db):
    fix_path = FIXTURES_DIR / "test_chlaw_anomaly_g.json"
    # Modifying 2 out of 3 articles (66.7% of the act > 50% threshold)
    laws = [{
        "LawName": "測試法規",
        "LawURL": "https://example.com/test_act",
        "LawModifiedDate": "2026-11-06",
        "LawArticles": [
            {"ArticleType": "A", "ArticleNo": "第 1 條", "ArticleContent": "異常變更1"},
            {"ArticleType": "A", "ArticleNo": "第 2 條", "ArticleContent": "異常變更2"},
            {"ArticleType": "A", "ArticleNo": "第 3 條", "ArticleContent": "第三條原始條文內容。"}
        ]
    }]
    create_chlaw_fixture(fix_path, laws)
    
    src = MojSource({"test_chlaw_file": str(fix_path)})
    conn = sqlite3.connect(temp_db)
    res = execute_update_run(src, apply=True, mode="test", conn=conn)
    assert res["status"] == "aborted_anomaly"
    assert "safety threshold" in res["error"]
    
    # Assert DB not written
    cur = conn.cursor()
    art1 = cur.execute("SELECT content FROM articles WHERE act_id = 'test_act' AND article_no = '1'").fetchone()
    assert art1[0] == "第一條原始條文內容。"
    conn.close()


# =====================================================================
# (h) apply 後 verify 失敗回滾
# =====================================================================
def test_case_h_verify_failure_rollback(temp_db):
    fix_path = FIXTURES_DIR / "test_chlaw_modify_h.json"
    laws = [{
        "LawName": "測試法規",
        "LawURL": "https://example.com/test_act",
        "LawModifiedDate": "2026-11-07",
        "LawArticles": [
            {"ArticleType": "A", "ArticleNo": "第 1 條", "ArticleContent": "第一條預計寫入"},
            {"ArticleType": "A", "ArticleNo": "第 2 條", "ArticleContent": "第二條原始條文內容。"},
            {"ArticleType": "A", "ArticleNo": "第 3 條", "ArticleContent": "第三條原始條文內容。"}
        ]
    }]
    create_chlaw_fixture(fix_path, laws)
    
    src = MojSource({"test_chlaw_file": str(fix_path)})
    # Force verification failure to test rollback
    src.verify = lambda apply_res, conn: (False, "Forced verification mismatch in test.")
    
    conn = sqlite3.connect(temp_db)
    res = execute_update_run(src, apply=True, mode="test", conn=conn)
    assert res["status"] == "verify_failed_rolled_back"
    
    # Assert rolled back: Art 1 content remains original
    cur = conn.cursor()
    art1 = cur.execute("SELECT content FROM articles WHERE act_id = 'test_act' AND article_no = '1'").fetchone()
    assert art1[0] == "第一條原始條文內容。"
    conn.close()


# =====================================================================
# (i) 連續執行兩次 (Idempotence: 2nd run reports no_change, row count unchanged)
# =====================================================================
def test_case_i_idempotence(temp_db):
    fix_path = FIXTURES_DIR / "test_chlaw_modify_i.json"
    laws = [{
        "LawName": "測試法規",
        "LawURL": "https://example.com/test_act",
        "LawModifiedDate": "2026-11-08",
        "LawArticles": [
            {"ArticleType": "A", "ArticleNo": "第 1 條", "ArticleContent": "第一條穩定修訂版。"},
            {"ArticleType": "A", "ArticleNo": "第 2 條", "ArticleContent": "第二條原始條文內容。"},
            {"ArticleType": "A", "ArticleNo": "第 3 條", "ArticleContent": "第三條原始條文內容。"}
        ]
    }]
    create_chlaw_fixture(fix_path, laws)
    
    src = MojSource({"test_chlaw_file": str(fix_path)})
    conn = sqlite3.connect(temp_db)
    
    # Run 1: Apply change
    res1 = execute_update_run(src, apply=True, mode="test", conn=conn)
    assert res1["status"] == "success"
    cur = conn.cursor()
    count_after_run1 = cur.execute("SELECT count(*) FROM articles").fetchone()[0]
    
    # Run 2: Continuous run with same data
    res2 = execute_update_run(src, apply=True, mode="test", conn=conn)
    assert res2["status"] == "no_change"
    count_after_run2 = cur.execute("SELECT count(*) FROM articles").fetchone()[0]
    assert count_after_run1 == count_after_run2
    conn.close()


# =====================================================================
# (j) stale 標記與重抓佇列
# =====================================================================
def test_case_j_stale_and_queue(temp_db):
    fix_path = FIXTURES_DIR / "test_chlaw_stale_j.json"
    laws = [{
        "LawName": "測試法規",
        "LawURL": "https://example.com/test_act",
        "LawModifiedDate": "2026-11-09",
        "LawArticles": [
            {"ArticleType": "A", "ArticleNo": "第 1 條", "ArticleContent": "第一條再次修訂。"},
            {"ArticleType": "A", "ArticleNo": "第 2 條", "ArticleContent": "第二條原始條文內容。"},
            {"ArticleType": "A", "ArticleNo": "第 3 條", "ArticleContent": "第三條原始條文內容。"}
        ]
    }]
    create_chlaw_fixture(fix_path, laws)
    
    src = MojSource({"test_chlaw_file": str(fix_path)})
    conn = sqlite3.connect(temp_db)
    execute_update_run(src, apply=True, mode="test", conn=conn)
    
    cur = conn.cursor()
    art1 = cur.execute("SELECT stale FROM articles WHERE act_id = 'test_act' AND article_no = '1'").fetchone()
    assert art1[0] == 1  # Stale marked
    
    # Queued in pending_lis
    pending = cur.execute("SELECT act_id, article_no, status FROM pending_lis WHERE act_id = 'test_act' AND article_no = '1'").fetchone()
    assert pending is not None
    assert pending[2] == "pending"
    conn.close()


# =====================================================================
# (k) pending_lis 8 週逾期處理
# =====================================================================
def test_case_k_pending_lis_expiry(temp_db):
    conn = sqlite3.connect(temp_db)
    cur = conn.cursor()
    # Insert pending item with 7 prior retries
    cur.execute("""
        INSERT INTO pending_lis (act_id, article_no, detected_at, retry_count, status)
        VALUES ('test_act', '1', '2026-09-01', 7, 'pending')
        ON CONFLICT(act_id, article_no) DO UPDATE SET retry_count = 7, status = 'pending'
    """)
    conn.commit()
    
    src = LisSource({"test_act_id": "test_act"})
    # Mock empty diff to simulate LIS still not having the reasons yet
    diff_res = {"changes": [], "counts": {}, "raw_path": "", "act_id": "test_act"}
    src.apply(diff_res, conn)
    
    item = cur.execute("SELECT retry_count, status FROM pending_lis WHERE act_id = 'test_act' AND article_no = '1'").fetchone()
    assert item[0] >= 8
    assert item[1] == "expired_8_weeks"
    conn.close()


# =====================================================================
# Safety Valve: > 10 acts abolished requires --confirm-abolish
# =====================================================================
def test_case_safety_valve_abolish_limit(temp_db):
    conn = sqlite3.connect(temp_db)
    cur = conn.cursor()
    # Create 15 active acts in DB
    for i in range(1, 16):
        cur.execute("""
            INSERT OR REPLACE INTO acts (id, name, category, status)
            VALUES (?, ?, '測試法規', 'active')
        """, (f"act_{i:02d}", f"測試法規{i:02d}"))
        cur.execute("""
            INSERT OR REPLACE INTO articles (act_id, article_no, content, status)
            VALUES (?, '1', '測試條文內容', 'active')
        """, (f"act_{i:02d}",))
    conn.commit()

    # Simulate remote ChLaw where 11 of these acts have LawAbandonNote = '廢'
    fix_path = FIXTURES_DIR / "test_chlaw_safety_valve.json"
    laws = []
    for i in range(1, 16):
        note = "廢" if i <= 11 else ""
        laws.append({
            "LawName": f"測試法規{i:02d}",
            "LawURL": f"https://example.com/act_{i:02d}",
            "LawModifiedDate": "2026-11-09",
            "LawAbandonNote": note,
            "LawArticles": [
                {"ArticleType": "A", "ArticleNo": "第 1 條", "ArticleContent": "測試條文內容"}
            ]
        })
    create_chlaw_fixture(fix_path, laws)

    src = MojSource({"test_chlaw_file": str(fix_path)})

    # Negative test: without confirm_abolish, run must abort immediately
    res_aborted = execute_update_run(src, apply=True, mode="test", conn=conn, confirm_abolish=False)
    assert res_aborted["status"] == "aborted_safety_valve"
    assert "exceeds safety limit of 10" in res_aborted["error"]

    # Verify database was NOT modified (all 15 acts remain active)
    active_count = cur.execute("SELECT count(*) FROM acts WHERE id LIKE 'act_%' AND status = 'active'").fetchone()[0]
    assert active_count == 15

    # Positive test: with confirm_abolish=True, safety valve is bypassed
    # (Allow anomaly check to pass by setting thresholds high enough)
    src.config["max_total_ratio"] = 1.0
    src.config["max_act_ratio"] = 1.0
    res_confirmed = execute_update_run(src, apply=True, mode="test", conn=conn, confirm_abolish=True)
    assert res_confirmed["status"] == "success"

    # Verify the 11 acts are now abolished
    abolished_count = cur.execute("SELECT count(*) FROM acts WHERE id LIKE 'act_%' AND status = 'abolished'").fetchone()[0]
    assert abolished_count == 11
    conn.close()


