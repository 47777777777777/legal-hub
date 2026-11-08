import os
import sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

def test_apa_128_screenshot():
    os.makedirs("reports/screenshots/lis_tier1_remote", exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        url = "http://161.33.166.144/#/act/admin_procedure_act/article/128"
        print("Navigating to:", url)
        page.goto(url, wait_until="networkidle", timeout=15000)

        card = page.locator("#article-card-128")
        card.wait_for(timeout=10000)
        card.locator(".article-study-btn").click()

        page.wait_for_selector("#study-drawer-scroll-body", timeout=8000)
        page.wait_for_timeout(600)

        tab_btn = page.locator('button.drawer-tab-btn[data-tab="legislative_history"]')
        tab_btn.click()
        page.wait_for_timeout(1000)

        content = page.locator("#drawer-tab-content-area")
        inner_html = content.inner_html()
        inner_text = content.inner_text()

        # Count occurrences of 1091230 reason
        reason_phrase = "就該法文中之「新證據」"
        count_reasons = inner_text.count(reason_phrase)
        print(f"Occurrences of 1091230 reason in drawer: {count_reasons} (Expected: 1)")

        has_mark = "<mark" in inner_html
        print(f"Has diff <mark> in HTML: {has_mark}")

        shot_path = "reports/screenshots/lis_tier1_remote/03_apa_art128_comparison_fixed.png"
        page.screenshot(path=shot_path)
        print("Saved updated screenshot to:", shot_path)

        browser.close()

if __name__ == "__main__":
    test_apa_128_screenshot()

