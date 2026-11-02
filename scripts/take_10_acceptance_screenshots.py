"""
scripts/take_10_acceptance_screenshots.py

Captures the 10 acceptance screenshots required by Prompt 3:
1. Tier 1 Act 1: Civil Procedure Code Art 244 (civil_procedure_code)
2. Tier 1 Act 2: Civil Code Art 2 (civil_code)
3. Tier 1 Act 3: Criminal Code Art 2 (criminal_code)
4. Tier 1 Act 4: Personal Data Protection Act Art 2 (personal_data_protection_act)
5. Tier 1 Act 5: Labor Standards Act Art 1 / Traffic Act
6. Judgment card close-up
7. Un-enriched article (clean official text + no-data notice)
8. Truthful paywalled legislative reasons notice ("法律人頁面標示本條有 N 段立法理由（會員內容），無法在此顯示")
9. Mobile layout view (viewport 375x667)
10. Data source provenance tag close-up ("來源：法律人")
"""

import os
import sys
import time
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREENSHOT_DIR = os.path.join(BASE_DIR, "reports", "screenshots", "prompt3")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

PORT = int(os.environ.get("PORT", 8080))
BASE_URL = os.environ.get("BASE_URL", f"http://127.0.0.1:{PORT}")


def take_screenshots():
    print(f"Connecting to Legal Hub at {BASE_URL} for 10 acceptance screenshots...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 850})
        page = context.new_page()

        # 1. Homepage & Civil Procedure Code Art 244
        print("[1/10] Capturing Tier 1 Act 1: CPC Art 244...")
        page.goto(BASE_URL)
        page.wait_for_selector("#study-drawer", state="attached", timeout=10000)
        page.evaluate("async () => { await window.legalHubApp.loadAct('civil_procedure_code'); await window.legalHubApp.openStudyDrawer('244'); }")
        time.sleep(1.0)
        p1 = os.path.join(SCREENSHOT_DIR, "01_tier1_act_cpc_244.png")
        page.screenshot(path=p1)
        print(f"  Saved: {p1}")

        # 2. Civil Code Art 2
        print("[2/10] Capturing Tier 1 Act 2: Civil Code Art 2...")
        page.evaluate("async () => { await window.legalHubApp.loadAct('civil_code'); await window.legalHubApp.openStudyDrawer('2'); }")
        time.sleep(1.0)
        p2 = os.path.join(SCREENSHOT_DIR, "02_tier1_act_civil_2.png")
        page.screenshot(path=p2)
        print(f"  Saved: {p2}")

        # 3. Criminal Code Art 2
        print("[3/10] Capturing Tier 1 Act 3: Criminal Code Art 2...")
        page.evaluate("async () => { await window.legalHubApp.loadAct('criminal_code'); await window.legalHubApp.openStudyDrawer('2'); }")
        time.sleep(1.0)
        p3 = os.path.join(SCREENSHOT_DIR, "03_tier1_act_criminal_2.png")
        page.screenshot(path=p3)
        print(f"  Saved: {p3}")

        # 4. Personal Data Protection Act Art 2
        print("[4/10] Capturing Tier 1 Act 4: PDPA Art 2...")
        page.evaluate("async () => { await window.legalHubApp.loadAct('personal_data_protection_act'); await window.legalHubApp.openStudyDrawer('2'); }")
        time.sleep(1.0)
        p4 = os.path.join(SCREENSHOT_DIR, "04_tier1_act_pdpa_2.png")
        page.screenshot(path=p4)
        print(f"  Saved: {p4}")

        # 5. Labor Standards Act Art 1 / Traffic Act
        print("[5/10] Capturing Tier 1 Act 5: Traffic Act Art 1...")
        page.evaluate("async () => { await window.legalHubApp.loadAct('traffic_act'); await window.legalHubApp.openStudyDrawer('1'); }")
        time.sleep(1.0)
        p5 = os.path.join(SCREENSHOT_DIR, "05_tier1_act_traffic_1.png")
        page.screenshot(path=p5)
        print(f"  Saved: {p5}")

        # 6. Judgment Card close-up (Insights tab in CPC 244)
        print("[6/10] Capturing Judgment Card close-up...")
        page.evaluate("async () => { await window.legalHubApp.loadAct('civil_procedure_code'); await window.legalHubApp.openStudyDrawer('244'); }")
        time.sleep(0.5)
        page.click('.drawer-tab-btn[data-tab="insights"]')
        time.sleep(0.5)
        p6 = os.path.join(SCREENSHOT_DIR, "06_judgment_card.png")
        judgment_el = page.query_selector(".judgment-card")
        if judgment_el:
            judgment_el.screenshot(path=p6)
        else:
            page.screenshot(path=p6)
        print(f"  Saved: {p6}")

        # 7. Un-enriched article (e.g. Traffic Act Art 80)
        print("[7/10] Capturing Un-enriched Article...")
        page.evaluate("async () => { await window.legalHubApp.loadAct('traffic_act'); await window.legalHubApp.openStudyDrawer('80'); }")
        time.sleep(0.8)
        p7 = os.path.join(SCREENSHOT_DIR, "07_unenriched_article.png")
        page.screenshot(path=p7)
        print(f"  Saved: {p7}")

        # 8. Paywalled Legislative Reasons Notice (Tab 4 in CPC 244)
        print("[8/10] Capturing Paywalled Legislative Reasons Notice...")
        page.evaluate("async () => { await window.legalHubApp.loadAct('civil_procedure_code'); await window.legalHubApp.openStudyDrawer('244'); }")
        time.sleep(0.5)
        page.click('.drawer-tab-btn[data-tab="legislative_history"]')
        time.sleep(0.5)
        p8 = os.path.join(SCREENSHOT_DIR, "08_paywalled_legislative_notice.png")
        page.screenshot(path=p8)
        print(f"  Saved: {p8}")

        # 9. Mobile Layout View (375 x 667)
        print("[9/10] Capturing Mobile View (iPhone SE)...")
        mobile_ctx = browser.new_context(viewport={"width": 375, "height": 667}, is_mobile=True)
        m_page = mobile_ctx.new_page()
        m_page.goto(BASE_URL)
        m_page.wait_for_selector("#study-drawer", state="attached", timeout=10000)
        m_page.evaluate("async () => { await window.legalHubApp.loadAct('civil_procedure_code'); await window.legalHubApp.openStudyDrawer('244'); }")
        time.sleep(0.8)
        p9 = os.path.join(SCREENSHOT_DIR, "09_mobile_layout.png")
        m_page.screenshot(path=p9)
        mobile_ctx.close()
        print(f"  Saved: {p9}")

        # 10. Data Source Provenance Tag close-up
        print("[10/10] Capturing Data Source Provenance Tag close-up...")
        page.click('.drawer-tab-btn[data-tab="key_knowledge"]')
        time.sleep(0.5)
        p10 = os.path.join(SCREENSHOT_DIR, "10_source_provenance_closeup.png")
        callout_el = page.query_selector(".callout-box")
        if callout_el:
            callout_el.screenshot(path=p10)
        else:
            page.screenshot(path=p10)
        print(f"  Saved: {p10}")

        browser.close()
    print("All 10 acceptance screenshots captured successfully!")


if __name__ == "__main__":
    take_screenshots()
