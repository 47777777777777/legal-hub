import os
import sys
import re
import time
import pytest
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.lis.parser import parse_full_act_reasons

TARGET_ARTICLES = [
    "1", "2", "10", "25", "44", "45", "50", "68", "85", "92",
    "100", "110", "120", "127", "128", "131", "140", "160", "174-1", "175"
]

def clean_for_assert(text):
    if not text:
        return ""
    return re.sub(r'\s+', '', text)

def get_expected_from_raw():
    s1_path = os.path.join(BASE_DIR, "data", "raw", "lis", "samples", "sample_1.html")
    with open(s1_path, "r", encoding="utf-8", errors="ignore") as f:
        html = f.read()
    records = parse_full_act_reasons(html)
    expected_map = {}
    for r in records:
        no = r['article_no']
        if no not in expected_map:
            expected_map[no] = []
        expected_map[no].append(r['reason'])
    return expected_map

def test_lis_20_articles_3_paths():
    expected_map = get_expected_from_raw()
    shots_dir = os.path.join(BASE_DIR, "reports", "screenshots", "lis_pilot")
    os.makedirs(shots_dir, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        # -------------------------------------------------------------
        # Path 1: Card Click in Act Stream View (for all 20 articles)
        # -------------------------------------------------------------
        print("\n--- Testing Path 1: Card Click (20 articles) ---")
        page.goto("http://127.0.0.1:8080/#/act/admin_procedure_act", wait_until="networkidle")
        page.wait_for_function(
            "() => window.legalHubApp && "
            "window.legalHubApp.currentAct && "
            "window.legalHubApp.currentAct.id === 'admin_procedure_act' && "
            "document.querySelectorAll('.stream-article-card').length === 176",
            timeout=15000
        )

        for art_no in TARGET_ARTICLES:
            card_sel = f"#article-card-{art_no}"
            card = page.locator(card_sel)
            # Scroll to card & click study button or card
            page.evaluate(f"window.legalHubApp.scrollToArticleCard('{art_no}')")
            page.wait_for_timeout(100)
            
            btn = card.locator(".article-study-btn")
            if btn.count() > 0:
                btn.click()
            else:
                card.click()
                
            page.wait_for_selector("#study-drawer:not(.hidden)", state="visible", timeout=5000)
            
            # Click Tab 4 (legislative_history)
            tab_btn = page.locator(".drawer-tab-btn[data-tab='legislative_history']")
            tab_btn.click()
            page.wait_for_timeout(100)
            
            drawer_content = page.locator("#drawer-tab-content-area").inner_text()
            clean_content = clean_for_assert(drawer_content)
            
            # Assert first 30 chars of expected reason from raw HTML
            expected_reasons = expected_map.get(art_no, [])
            assert len(expected_reasons) > 0, f"Raw file has no reasons for Art {art_no}"
            first_reason_clean = clean_for_assert(expected_reasons[0])
            check_str = first_reason_clean[:30]
            assert check_str in clean_content, f"Path 1 mismatch for Art {art_no}: expected '{check_str}' in Tab 4 content"

        # -------------------------------------------------------------
        # Path 2: Permalink Hash Routing (for all 20 articles)
        # -------------------------------------------------------------
        print("\n--- Testing Path 2: Permalink Hash (20 articles) ---")
        for art_no in TARGET_ARTICLES:
            hash_url = f"http://127.0.0.1:8080/#/act/admin_procedure_act/article/{art_no}"
            page.goto(hash_url, wait_until="networkidle")
            page.wait_for_selector("#study-drawer:not(.hidden)", state="visible", timeout=5000)
            
            tab_btn = page.locator(".drawer-tab-btn[data-tab='legislative_history']")
            tab_btn.click()
            page.wait_for_timeout(100)
            
            drawer_content = page.locator("#drawer-tab-content-area").inner_text()
            clean_content = clean_for_assert(drawer_content)
            
            expected_reasons = expected_map.get(art_no, [])
            first_reason_clean = clean_for_assert(expected_reasons[0])
            check_str = first_reason_clean[:30]
            assert check_str in clean_content, f"Path 2 mismatch for Art {art_no}: expected '{check_str}' in Tab 4 content"

        # -------------------------------------------------------------
        # Path 3: Quick Dialer Jump (for all 20 articles)
        # -------------------------------------------------------------
        print("\n--- Testing Path 3: Quick Dialer (20 articles) ---")
        page.goto("http://127.0.0.1:8080/#/act/admin_procedure_act", wait_until="networkidle")
        page.wait_for_selector(".stream-article-card", timeout=10000)

        for art_no in TARGET_ARTICLES:
            # Trigger jump via dialer
            page.evaluate(f"window.legalHubApp.loadAndJumpArticle('{art_no}')")
            page.wait_for_selector("#study-drawer:not(.hidden)", state="visible", timeout=5000)
            
            tab_btn = page.locator(".drawer-tab-btn[data-tab='legislative_history']")
            tab_btn.click()
            page.wait_for_timeout(100)
            
            drawer_content = page.locator("#drawer-tab-content-area").inner_text()
            clean_content = clean_for_assert(drawer_content)
            
            expected_reasons = expected_map.get(art_no, [])
            first_reason_clean = clean_for_assert(expected_reasons[0])
            check_str = first_reason_clean[:30]
            assert check_str in clean_content, f"Path 3 mismatch for Art {art_no}: expected '{check_str}' in Tab 4 content"

        # -------------------------------------------------------------
        # Screenshot 1: Single version article (Art 1)
        # -------------------------------------------------------------
        page.goto("http://127.0.0.1:8080/#/act/admin_procedure_act/article/1", wait_until="networkidle")
        page.wait_for_selector("#study-drawer:not(.hidden)", state="visible", timeout=5000)
        page.locator(".drawer-tab-btn[data-tab='legislative_history']").click()
        page.wait_for_timeout(300)
        shot1 = os.path.join(shots_dir, "single_version_art1.png")
        page.screenshot(path=shot1)
        print(f"Captured screenshot 1: {shot1}")

        # -------------------------------------------------------------
        # Screenshot 2: Multi-version article with comparison table (Art 128)
        # -------------------------------------------------------------
        page.goto("http://127.0.0.1:8080/#/act/admin_procedure_act/article/128", wait_until="networkidle")
        page.wait_for_selector("#study-drawer:not(.hidden)", state="visible", timeout=5000)
        page.locator(".drawer-tab-btn[data-tab='legislative_history']").click()
        page.wait_for_timeout(300)
        
        # Verify comparison table header on Art 128
        comp_content = page.locator("#drawer-tab-content-area").inner_text()
        assert "第一百二十八條" in comp_content
        assert "版本條文" in comp_content or "對照表" in comp_content
        
        shot2 = os.path.join(shots_dir, "multi_version_art128.png")
        page.screenshot(path=shot2)
        print(f"Captured screenshot 2: {shot2}")

        # -------------------------------------------------------------
        # Screenshot 3: No-data article (Civil Procedure Code Art 2)
        # -------------------------------------------------------------
        page.goto("http://127.0.0.1:8080/#/act/civil_procedure_code/article/2", wait_until="networkidle")
        page.wait_for_function(
            "() => window.legalHubApp && "
            "window.legalHubApp.currentActId === 'civil_procedure_code' && "
            "window.legalHubApp.selectedArticleNo === '2'",
            timeout=10000
        )
        page.wait_for_selector("#study-drawer:not(.hidden)", state="visible", timeout=5000)
        page.locator(".drawer-tab-btn[data-tab='legislative_history']").click()
        page.wait_for_timeout(300)
        
        empty_content = page.locator("#drawer-tab-content-area").inner_text()
        assert "立法院法律系統無此條資料" in empty_content, f"Expected empty message in CPC Art 2 Tab 4, got: {empty_content}"
        
        shot3 = os.path.join(shots_dir, "no_data_cpc_art2.png")
        page.screenshot(path=shot3)
        print(f"Captured screenshot 3: {shot3}")

        browser.close()

if __name__ == "__main__":
    test_lis_20_articles_3_paths()
    print("ALL 20 ARTICLES x 3 PATHS PLAYWRIGHT TESTS PASSED!")
