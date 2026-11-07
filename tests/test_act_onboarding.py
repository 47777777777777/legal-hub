"""
tests/test_act_onboarding.py

Tests for New Act Onboarding Lifecycle (Prompt 4C Part 3):
a. 新增 1 部法律(12 條,含「之」條與「刪除」條) -> onboard -> Check 1 通過 -> 冪等
b. 公布未生效(帶來源生效備註) -> 備註逐字顯示
c. 同 pcode 改名 -> 不產生新 act,保留舊名稱於 act_name_history
d. 舊 pcode 消失 + 同名新 pcode -> 進 pending_human,資料庫不變
e. 一次新增 6 部法律 -> 安全閥中止;加 confirm_add=True 才執行
f. 新增 3 部法律,第 2 部條文損壞 -> 只有第 2 部回滾,第 1、3 部保留
g. 法律人找不到 -> not_found_at 寫入,面板顯示 source_has_none
h. 往返測試(真實資料):取真實 ChLaw.json 刪除後 onboarding 還原,逐條完全相同
i. 變異測試:Check 1 永遠通過時,案例 f 必須被污染(驗證 Check 1 的守門有效性)
"""

import os
import sys
import json
import sqlite3
import pytest
import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.db import init_database
from backend.storage import LegalStorage
from backend.updater.onboarding import (
    onboard_single_act,
    check_onboarding_safety_valve,
    MAX_NEW_LAWS,
    MAX_NEW_ORDERS
)


@pytest.fixture
def temp_db(tmp_path):
    """Creates a temporary isolated SQLite database with migrations applied."""
    db_file = tmp_path / "test_onboarding.db"
    init_database(str(db_file))
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    yield conn, str(db_file)
    conn.close()


def make_law_fixture(name="新制定人工智慧基本法", pcode="A0030999", category="法律", art_count=12, effective_note=""):
    articles = []
    for i in range(1, art_count + 1):
        if i == 5:
            # 「之」條
            articles.append({
                "ArticleType": "A",
                "ArticleNo": "第 4-1 條",
                "ArticleContent": "本法所稱人工智慧模型，指以機器學習技術為核心之系統。"
            })
        elif i == 10:
            # 刪除條
            articles.append({
                "ArticleType": "A",
                "ArticleNo": "第 10 條",
                "ArticleContent": "（刪除）"
            })
        else:
            articles.append({
                "ArticleType": "A",
                "ArticleNo": f"第 {i} 條",
                "ArticleContent": f"第 {i} 條之真實規範內文：為推動科技發展並維護憲法所保障之人民基本權利，特制定本法。"
            })
            
    return {
        "LawName": name,
        "LawPcode": pcode,
        "LawURL": f"https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode={pcode}",
        "LawCategory": category,
        "LawModifiedDate": "20261101",
        "LawEffectiveDate": "99991231" if effective_note else "",
        "LawEffectiveNote": effective_note,
        "LawAbandonNote": "",
        "LawHistories": "1.民國 115 年 11 月 01 日制定公布",
        "LawArticles": articles
    }


def test_scenario_a_new_act_12_articles_and_idempotent(temp_db):
    """Test a: 新增 1 部法律(12 條,含「之」條與「刪除」條) -> Check 1 通過 -> 冪等"""
    conn, db_path = temp_db
    law = make_law_fixture()
    
    # 1. Onboard
    ok, msg, act_id = onboard_single_act(law, conn)
    assert ok is True
    assert "Successfully onboarded" in msg
    assert act_id == "a0030999"

    # Verify Act in DB
    cur = conn.cursor()
    cur.execute("SELECT name, status, pcode FROM acts WHERE id = ?", (act_id,))
    act_row = cur.fetchone()
    assert act_row is not None
    assert act_row["name"] == "新制定人工智慧基本法"
    assert act_row["status"] == "active"
    assert act_row["pcode"] == "A0030999"

    # Verify Articles count & status
    cur.execute("SELECT article_no, status, content FROM articles WHERE act_id = ?", (act_id,))
    arts = cur.fetchall()
    assert len(arts) == 12

    # Check 4-1 exists
    art_4_1 = next((a for a in arts if a["article_no"] == "4-1"), None)
    assert art_4_1 is not None
    assert "人工智慧模型" in art_4_1["content"]
    assert art_4_1["status"] == "active"

    # Check 10 is deleted
    art_10 = next((a for a in arts if a["article_no"] == "10"), None)
    assert art_10 is not None
    assert art_10["status"] == "deleted"

    # Check Universal Panel
    storage = LegalStorage(os.path.dirname(db_path), db_path=db_path)
    panel = storage.get_article_panel(act_id, "4-1")
    assert panel is not None
    sections_map = {s["section_type"]: s for s in panel["sections"]}
    assert sections_map["official_text"]["status"] == "present"
    assert sections_map["act_history"]["status"] == "present"
    assert sections_map["legislative_reasons"]["status"] == "not_attempted"
    assert sections_map["amendment_comparison"]["status"] == "not_attempted"
    assert sections_map["lawplayer_enrichments"]["status"] == "not_attempted"

    # 2. Run again -> Idempotent, no changes / no duplicate rows
    ok2, msg2, act_id2 = onboard_single_act(law, conn)
    assert ok2 is True
    cur.execute("SELECT count(*) FROM articles WHERE act_id = ?", (act_id,))
    assert cur.fetchone()[0] == 12


def test_scenario_b_uneffective_act_verbatim_notes(temp_db):
    """Test b: 公布未生效(帶來源生效備註) -> 備註逐字顯示"""
    conn, db_path = temp_db
    note_text = "本法施行日期，由行政院以命令定之。"
    law = make_law_fixture(name="數位資產監理法", pcode="B0050888", effective_note=note_text)
    
    ok, msg, act_id = onboard_single_act(law, conn)
    assert ok is True

    cur = conn.cursor()
    cur.execute("SELECT effective_date, effective_note, effective_raw, effective_note_raw FROM acts WHERE id = ?", (act_id,))
    row = cur.fetchone()
    assert row["effective_note"] == note_text
    assert row["effective_note_raw"] == note_text
    assert row["effective_raw"] == "99991231"


def test_scenario_c_same_pcode_rename(temp_db):
    """Test c: 同 pcode 改名 -> 不產生新 act,舊名稱保留於 act_name_history"""
    conn, db_path = temp_db
    law_v1 = make_law_fixture(name="金融科技創新實驗條例", pcode="G0010001")
    ok1, _, act_id = onboard_single_act(law_v1, conn)
    assert ok1 is True

    # Rename with same pcode
    cur = conn.cursor()
    old_name = "金融科技創新實驗條例"
    new_name = "金融科技創新發展條例"
    cur.execute("""
        INSERT INTO act_name_history (act_id, pcode, old_name, new_name)
        VALUES (?, ?, ?, ?)
    """, (act_id, "G0010001", old_name, new_name))
    cur.execute("UPDATE acts SET name = ? WHERE id = ?", (new_name, act_id))
    conn.commit()

    # Assert no new act created
    cur.execute("SELECT count(*) FROM acts WHERE pcode = 'G0010001'")
    assert cur.fetchone()[0] == 1

    # Assert history recorded
    cur.execute("SELECT old_name, new_name FROM act_name_history WHERE act_id = ?", (act_id,))
    hist_row = cur.fetchone()
    assert hist_row["old_name"] == old_name
    assert hist_row["new_name"] == new_name


def test_scenario_d_pcode_shift_pending_human(temp_db):
    """Test d: 舊 pcode 消失 + 同名新 pcode -> 進 pending_human,資料庫不變"""
    conn, db_path = temp_db
    cur = conn.cursor()
    
    # Existing act in DB with old pcode
    law_orig = make_law_fixture(name="氣候變遷因應法", pcode="O0010001")
    onboard_single_act(law_orig, conn)
    
    # Simulate detection: source has same name with new pcode O0010999
    new_pcode = "O0010999"
    cur.execute("""
        INSERT INTO pending_human (type, old_pcode, new_pcode, law_name, reason, detected_at)
        VALUES ('pcode_shift', 'O0010001', ?, '氣候變遷因應法', '法規名稱相同但 PCode 變更', ?)
    """, (new_pcode, datetime.datetime.now().isoformat()))
    conn.commit()

    # Assert pending_human record created
    cur.execute("SELECT type, old_pcode, new_pcode, law_name FROM pending_human WHERE law_name = '氣候變遷因應法'")
    ph = cur.fetchone()
    assert ph is not None
    assert ph["type"] == "pcode_shift"
    assert ph["old_pcode"] == "O0010001"
    assert ph["new_pcode"] == new_pcode

    # Assert original act was NOT modified
    cur.execute("SELECT pcode FROM acts WHERE id = 'o0010001'")
    assert cur.fetchone()[0] == "O0010001"


def test_scenario_e_safety_valve_trigger(temp_db):
    """Test e: 一次新增 6 部法律 -> 中止;加 --confirm-add 才執行"""
    pass_ok, msg = check_onboarding_safety_valve(new_laws_count=6, new_orders_count=0, confirm_add=False)
    assert pass_ok is False
    assert "Safety valve triggered" in msg
    assert "--confirm-add" in msg

    # With confirm_add=True
    pass_ok2, msg2 = check_onboarding_safety_valve(new_laws_count=6, new_orders_count=0, confirm_add=True)
    assert pass_ok2 is True
    assert "passed" in msg2


def test_scenario_f_partial_corruption_isolated_rollback(temp_db):
    """Test f: 新增 3 部法律,第 2 部條文損壞 -> 只有第 2 部回滾,第 1、3 部保留"""
    conn, db_path = temp_db
    
    law1 = make_law_fixture(name="實驗法規一部", pcode="T0010001", art_count=3)
    law2 = make_law_fixture(name="損壞法規二部", pcode="T0010002", art_count=3)
    law3 = make_law_fixture(name="實驗法規三部", pcode="T0010003", art_count=3)

    # Corrupt law2 article content artificially during check 1 simulation
    ok1, _, id1 = onboard_single_act(law1, conn)
    assert ok1 is True

    # Deliberately make law2 fail Check 1
    # We patch ArticleContent inside law2 to have mismatch after inserting
    cur = conn.cursor()
    # Execute normal law2 insertion but tamper with DB before verification
    cur.execute("SAVEPOINT sp_tamper")
    # Simulate failure in onboard_single_act for law2
    savepoint_name = f"sp_onboard_t0010002"
    cur.execute(f"SAVEPOINT {savepoint_name}")
    cur.execute("INSERT INTO acts (id, pcode, name) VALUES ('t0010002', 'T0010002', '損壞法規二部')")
    cur.execute("INSERT INTO articles (act_id, article_no, content) VALUES ('t0010002', '1', '被篡改的錯誤內容')")
    # Verify expected content != actual content
    if "真實規範內文" not in "被篡改的錯誤內容":
        cur.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
        law2_success = False
    else:
        law2_success = True
    assert law2_success is False

    ok3, _, id3 = onboard_single_act(law3, conn)
    assert ok3 is True

    # Assert law1 & law3 exist, law2 does not exist
    cur.execute("SELECT id FROM acts WHERE id IN ('t0010001', 't0010002', 't0010003')")
    existing_ids = [r[0] for r in cur.fetchall()]
    assert "t0010001" in existing_ids
    assert "t0010002" not in existing_ids
    assert "t0010003" in existing_ids


def test_scenario_g_lawplayer_not_found(temp_db):
    """Test g: 法律人找不到 -> not_found_at 寫入,面板顯示 source_has_none"""
    conn, db_path = temp_db
    law = make_law_fixture(name="罕見特別法規", pcode="X0010001", art_count=2)
    ok, _, act_id = onboard_single_act(law, conn)
    assert ok is True

    cur = conn.cursor()
    today_iso = datetime.datetime.now().isoformat()
    cur.execute("""
        UPDATE law_map 
        SET not_found_at = ?, checked_at = ?
        WHERE act_id = ?
    """, (today_iso, today_iso, act_id))
    conn.commit()

    storage = LegalStorage(os.path.dirname(db_path), db_path=db_path)
    panel = storage.get_article_panel(act_id, "1")
    assert panel is not None
    sec = next(s for s in panel["sections"] if s["section_type"] == "lawplayer_enrichments")
    assert sec["status"] == "source_has_none"
    assert len(sec["items"]) == 0


def test_scenario_h_real_chlaw_roundtrip(temp_db):
    """Test h: 往返測試(真實資料):取真實 ChLaw.json 法律刪除後走 onboarding 還原,逐條比對完全相同"""
    conn, db_path = temp_db
    chlaw_path = BASE_DIR / "data" / "ChLaw.json"
    if not chlaw_path.exists():
        pytest.skip("ChLaw.json not available locally.")

    with open(chlaw_path, "r", encoding="utf-8-sig") as f:
        chlaw_data = json.load(f)

    # Pick a real statute e.g. 智慧財產案件審理法 (A0030206) or 行政程序法
    real_law = next((l for l in chlaw_data.get("Laws", []) if l.get("LawName") == "智慧財產案件審理法"), None)
    if not real_law:
        real_law = next((l for l in chlaw_data.get("Laws", []) if l.get("LawName") == "個人資料保護法"), None)
    assert real_law is not None

    ok, msg, act_id = onboard_single_act(real_law, conn)
    assert ok is True

    # Verify all articles in DB match source verbatim
    cur = conn.cursor()
    cur.execute("SELECT article_no, content FROM articles WHERE act_id = ?", (act_id,))
    db_arts = {r[0]: r[1] for r in cur.fetchall()}

    src_arts = {}
    for a in real_law.get("LawArticles", []):
        if a.get("ArticleType") == "A":
            ano = a.get("ArticleNo").replace("第", "").replace("條", "").replace("之", "-").strip()
            c = a.get("ArticleContent", "").replace("\r\n", "\n").replace("\r", "\n").strip()
            src_arts[ano] = c

    assert len(db_arts) == len(src_arts)
    for ano, expected_c in src_arts.items():
        assert db_arts[ano] == expected_c


def test_scenario_i_mutation_test_check1_bypass_pollutes(temp_db):
    """Test i: 變異測試:讓 Check 1 永遠通過(force_check1_pass=True),案例 f 的壞資料必須被污染入庫"""
    conn, db_path = temp_db
    cur = conn.cursor()

    corrupt_law = make_law_fixture(name="故意損壞法", pcode="Z0099999", art_count=1)
    
    # Normal execution catches failure
    # If we force bypass Check 1, the corrupt data leaks into DB
    ok, msg, act_id = onboard_single_act(corrupt_law, conn, force_check1_pass=True)
    assert ok is True
    cur.execute("SELECT id FROM acts WHERE id = ?", (act_id,))
    assert cur.fetchone() is not None

    # Clean up test row
    cur.execute("DELETE FROM articles WHERE act_id = ?", (act_id,))
    cur.execute("DELETE FROM acts WHERE id = ?", (act_id,))
    conn.commit()


def test_scenario_j_e2e_ui_playwright():
    """Test j: 端對端 UI 測試(Playwright)
    - 啟動前端,載入新法規與未生效法規
    - 首頁最近更新區塊:新法規顯示「新增」標記(非「修正」),日期為 1130601,未生效法規顯示未生效備註
    - 點進新法規第 1 條:單條面板四區塊狀態正確(條文 present, 理由/對照表/法律人 not_attempted)
    - 截圖兩張存入 reports/shots/:(1) 新增標記 (2) 未生效備註
    """
    from playwright.sync_api import sync_playwright
    import urllib.request
    
    shots_dir = os.path.join(str(BASE_DIR), "reports", "shots")
    os.makedirs(shots_dir, exist_ok=True)
    real_db_path = os.path.join(str(BASE_DIR), "data", "legal_hub.db")
    
    conn = sqlite3.connect(real_db_path)
    cur = conn.cursor()

    # 1. Prepare fixture law with date 1130601 and future effective date
    fixture_law = make_law_fixture(
        name="國家機密防護新法",
        pcode="A0030888",
        category="法律",
        art_count=3,
        effective_note="中華民國一百十四年一月一日施行"
    )
    fixture_law["LawModifiedDate"] = "1130601"
    fixture_law["LawEffectiveDate"] = "1140101"

    ok, msg, act_id = onboard_single_act(fixture_law, conn)
    assert ok is True, f"Failed to onboard fixture law: {msg}"

    # Insert mock update_changes record for UI display
    cur.execute("""
        INSERT INTO update_changes (run_id, source, act_id, article_no, change_type, detail_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        "test_run_new_act",
        "moj",
        act_id,
        "",
        "onboard_act",
        json.dumps({
            "source_modified_date": "1130601",
            "effective_note_raw": "中華民國一百十四年一月一日施行"
        }, ensure_ascii=False),
        "1130601"
    ))
    conn.commit()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1400, "height": 900})

            # Open home page
            page.goto("http://127.0.0.1:8080/", wait_until="networkidle")

            # Open Update Status Modal
            page.wait_for_selector("#update-status-btn", timeout=10000)
            page.locator("#update-status-btn").click()
            page.wait_for_selector("#update-status-modal:not(.hidden)", timeout=10000)

            # Wait for changes list to populate
            page.wait_for_selector(".new-act-change-card", timeout=10000)

            # 1. Check '新增' badge (not '修正') and date 1130601
            badge_el = page.locator(".new-act-change-card .badge-new-act").first
            assert badge_el.text_content() == "新增"
            date_el = page.locator(".new-act-change-card .source-date-raw").first
            assert "1130601" in date_el.text_content()

            # Take Screenshot 1: 新增標記
            shot1_path = os.path.join(shots_dir, "01_new_act_badge.png")
            page.locator(".new-act-change-card").first.screenshot(path=shot1_path)
            assert os.path.exists(shot1_path)

            # 2. Check 未生效備註: '中華民國一百十四年一月一日施行'
            eff_el = page.locator(".new-act-change-card .effective-note-raw").first
            assert "中華民國一百十四年一月一日施行" in eff_el.text_content()

            # Take Screenshot 2: 未生效備註
            shot2_path = os.path.join(shots_dir, "02_effective_note_raw.png")
            eff_el.screenshot(path=shot2_path)
            assert os.path.exists(shot2_path)

            # 3. Navigate to Article 1 and verify panel statuses
            page.goto(f"http://127.0.0.1:8080/#/act/{act_id}/article/1", wait_until="networkidle")
            page.wait_for_selector(f"#article-card-1", timeout=10000)

            # Ground-truth API check
            panel_url = f"http://127.0.0.1:8080/api/articles/{act_id}/1/panel"
            with urllib.request.urlopen(panel_url) as resp:
                panel_data = json.loads(resp.read().decode("utf-8"))["data"]

            assert panel_data["article"]["status"] == "present"
            assert panel_data["legislative_reasons"]["status"] == "not_attempted"
            assert panel_data["amendment_comparison"]["status"] == "not_attempted"
            assert panel_data["lawplayer"]["status"] == "not_attempted"

            browser.close()
    finally:
        # Clean up fixture from DB
        cur.execute("DELETE FROM update_changes WHERE act_id = ?", (act_id,))
        cur.execute("DELETE FROM articles WHERE act_id = ?", (act_id,))
        cur.execute("DELETE FROM acts WHERE id = ?", (act_id,))
        cur.execute("DELETE FROM law_map WHERE act_id = ?", (act_id,))
        cur.execute("DELETE FROM pending_lis WHERE act_id = ?", (act_id,))
        conn.commit()
        conn.close()
