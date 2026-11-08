import os
import sys
import time
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

REMOTE_BASE = "http://161.33.166.144"

TEST_ARTICLES = [
    ("admin_procedure_act", "1", "行政程序法 第 1 條 (單一版本)"),
    ("admin_procedure_act", "128", "行政程序法 第 128 條 (多版本對照表)"),
    ("criminal_code", "10", "刑法 第 10 條 (多版本)"),
    ("criminal_code", "296-1", "刑法 第 296-1 條 (枝條號)"),
    ("civil_code", "15", "民法 第 15 條 (多版本)"),
    ("traffic_act", "12", "道路交通管理處罰條例 第 12 條"),
    ("labor_standards_act", "32", "勞動基準法 第 32 條"),
    ("company_act", "9", "公司法 第 9 條"),
    ("civil_procedure_code", "244", "民事訴訟法 第 244 條"),
    ("criminal_procedure_code", "160", "刑事訴訟法 第 160 條"),
    ("a0030154", "2", "行政訴訟法 第 2 條"),
    ("constitution", "1", "中華民國憲法 第 1 條"),
    ("criminal_code", "5", "刑法 第 5 條"),
    ("criminal_code", "6", "刑法 第 6 條"),
    ("civil_code", "1", "民法 第 1 條"),
    ("labor_standards_act", "2", "勞動基準法 第 2 條"),
    ("company_act", "1", "公司法 第 1 條"),
    ("traffic_act", "1", "道路交通管理處罰條例 第 1 條"),
    ("civil_procedure_code", "1", "民事訴訟法 第 1 條"),
    ("criminal_procedure_code", "1", "刑事訴訟法 第 1 條"),
]

def run_tier1_playwright_verification():
    os.makedirs("reports/screenshots/lis_tier1_remote", exist_ok=True)
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))

        print(f"=== Starting Playwright Remote Verification ({len(TEST_ARTICLES)} Articles) against {REMOTE_BASE} ===")

        for idx, (act_id, art_no, label) in enumerate(TEST_ARTICLES, start=1):
            url = f"{REMOTE_BASE}/#/act/{act_id}/article/{art_no}"
            print(f"[{idx}/{len(TEST_ARTICLES)}] Checking: {label} -> {url}")
            try:
                page.goto(url, wait_until="networkidle", timeout=15000)
                card_sel = f"#article-card-{art_no}"
                page.wait_for_selector(card_sel, timeout=10000)
                card = page.locator(card_sel)

                # Open study drawer
                study_btn = card.locator(".article-study-btn")
                study_btn.click()
                page.wait_for_selector("#study-drawer-scroll-body", timeout=8000)
                page.wait_for_timeout(600)

                # Switch to Tab 4: 立法理由與沿革
                tab_btn = page.locator('button.drawer-tab-btn[data-tab="legislative_history"]')
                tab_btn.click()
                page.wait_for_timeout(800)

                # Check content of tab 4
                tab_content = page.locator("#drawer-tab-content-area").inner_text()

                has_reason = ("立法院法律系統" in tab_content or "民國" in tab_content or "條" in tab_content or "理由" in tab_content)
                has_no_attempted = ("尚未查詢" in tab_content)

                status = "PASS" if (has_reason and not has_no_attempted) or ("無此條資料" in tab_content) else "WARN"
                print(f"    Drawer Content Status: {status} (Chars: {len(tab_content)})")
                results.append((idx, act_id, art_no, label, status, len(tab_content)))

                # 3 Mandated Screenshots
                # 1. Single-version article (admin_procedure_act 1)
                if act_id == "admin_procedure_act" and art_no == "1":
                    shot_path = "reports/screenshots/lis_tier1_remote/01_single_version_apa_art1.png"
                    page.screenshot(path=shot_path)
                    print(f"    Captured Screenshot 1: {shot_path}")

                # 2. Multi-version comparison table (criminal_code 10 or apa 128)
                if act_id == "criminal_code" and art_no == "10":
                    shot_path = "reports/screenshots/lis_tier1_remote/02_multi_version_criminal_art10.png"
                    page.screenshot(path=shot_path)
                    print(f"    Captured Screenshot 2: {shot_path}")

                # 3. Administrative Procedure Act Art 128
                if act_id == "admin_procedure_act" and art_no == "128":
                    shot_path = "reports/screenshots/lis_tier1_remote/03_apa_art128_comparison.png"
                    page.screenshot(path=shot_path)
                    print(f"    Captured Screenshot 3: {shot_path}")

                # Close drawer
                close_btn = page.locator("#study-drawer-close-btn")
                if close_btn.count() > 0 and close_btn.is_visible():
                    close_btn.click()
                    page.wait_for_timeout(300)

            except Exception as e:
                print(f"    ERROR on {label}: {e}")
                results.append((idx, act_id, art_no, label, f"FAIL: {e}", 0))

        browser.close()

    print("\n=== Playwright Remote Verification Summary ===")
    for idx, act_id, art_no, label, status, length in results:
        print(f"  {idx:2d}. {label:<35}: {status} (content len: {length})")
    
    passed_count = sum(1 for r in results if r[4] == "PASS")
    print(f"\nTotal Passed: {passed_count}/{len(results)}")
    assert passed_count >= 18, f"Too many failures in Playwright remote verification: {passed_count}/{len(results)}"

if __name__ == "__main__":
    run_tier1_playwright_verification()
