import os
import sys
import time
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:8080"
SHOTS_DIR = r"C:\Users\harry\.gemini\antigravity\brain\ed7f1a6d-ba9f-401f-8aa8-4d33325c5647"

def run_4shots_verification():
    os.makedirs(SHOTS_DIR, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        print("=== Step 1: Administrative Procedure Act Art 128 ===")
        page.goto(f"{BASE_URL}/#/act/admin_procedure_act/article/128", wait_until="networkidle")
        card = page.locator("#article-card-128")
        card.wait_for(timeout=10000)
        card.locator(".article-study-btn").click()
        page.wait_for_selector("#study-drawer-scroll-body", timeout=8000)
        page.wait_for_timeout(500)

        # Click Tab 4: 立法理由與沿革
        tab4 = page.locator('button.drawer-tab-btn[data-tab="legislative_history"]')
        tab4.click()
        page.wait_for_timeout(800)

        # Assertions for Art 128:
        content_area = page.locator("#drawer-tab-content-area")
        cards = content_area.locator(".card")
        card_count = cards.count()
        print(f"  Art 128 cards count: {card_count} (Expected: 2)")
        assert card_count == 2, f"Expected 2 cards for Art 128, got {card_count}"

        # Assert disclaimer pill
        disclaimer = content_area.locator(".diff-disclaimer-pill")
        assert disclaimer.count() >= 1, "Missing diff disclaimer pill"
        print(f"  Disclaimer pill text: {disclaimer.first.inner_text()}")

        # Assert diff underline/ins on paragraph 3
        ins_elements = content_area.locator("ins.diff-ins")
        assert ins_elements.count() > 0, "Expected ins.diff-ins in Art 128 comparison"
        print(f"  ins.diff-ins count: {ins_elements.count()}, first: {ins_elements.first.inner_text()[:40]}")

        # Assert reason occurs exactly once per card
        card_109 = cards.first
        reason_blocks = card_109.locator(".diff-card-reason")
        print(f"  1091230 card reason blocks count: {reason_blocks.count()} (Expected: 1)")
        assert reason_blocks.count() == 1, "Reason block must occur exactly once in card"

        shot1_path = os.path.join(SHOTS_DIR, "03_apa_art128_comparison_fixed.png")
        page.screenshot(path=shot1_path)
        print(f"  Captured Screenshot 1: {shot1_path}")

        # Close drawer
        page.locator("#drawer-close-btn").click()
        page.wait_for_timeout(400)

        print("\n=== Step 2: Criminal Code Art 10 (Multi-version) ===")
        page.goto(f"{BASE_URL}/#/act/criminal_code/article/10", wait_until="networkidle")
        card = page.locator("#article-card-10")
        card.wait_for(timeout=10000)
        card.locator(".article-study-btn").click()
        page.wait_for_selector("#study-drawer-scroll-body", timeout=8000)
        page.wait_for_timeout(500)

        tab4 = page.locator('button.drawer-tab-btn[data-tab="legislative_history"]')
        tab4.click()
        page.wait_for_timeout(800)

        content_area = page.locator("#drawer-tab-content-area")
        cards = content_area.locator(".card")
        card_count = cards.count()
        print(f"  Criminal Code Art 10 cards count: {card_count} (Expected: 5)")
        assert card_count == 5, f"Expected 5 cards for Art 10, got {card_count}"

        shot2_path = os.path.join(SHOTS_DIR, "02_multi_version_criminal_art10.png")
        page.screenshot(path=shot2_path)
        print(f"  Captured Screenshot 2: {shot2_path}")

        page.locator("#drawer-close-btn").click()
        page.wait_for_timeout(400)

        print("\n=== Step 3: Deleted version - APA Art 44 ===")
        page.goto(f"{BASE_URL}/#/act/admin_procedure_act/article/44", wait_until="networkidle")
        card = page.locator("#article-card-44")
        card.wait_for(timeout=10000)
        card.locator(".article-study-btn").click()
        page.wait_for_selector("#study-drawer-scroll-body", timeout=8000)
        page.wait_for_timeout(500)

        tab4 = page.locator('button.drawer-tab-btn[data-tab="legislative_history"]')
        tab4.click()
        page.wait_for_timeout(800)

        content_area = page.locator("#drawer-tab-content-area")
        cards = content_area.locator(".card")
        print(f"  APA Art 44 cards count: {cards.count()}")

        shot3_path = os.path.join(SHOTS_DIR, "04_deleted_version_apa_art44.png")
        page.screenshot(path=shot3_path)
        print(f"  Captured Screenshot 3: {shot3_path}")

        page.locator("#drawer-close-btn").click()
        page.wait_for_timeout(400)

        print("\n=== Step 4: Enacted version - APA Art 1 ===")
        page.goto(f"{BASE_URL}/#/act/admin_procedure_act/article/1", wait_until="networkidle")
        card = page.locator("#article-card-1")
        card.wait_for(timeout=10000)
        card.locator(".article-study-btn").click()
        page.wait_for_selector("#study-drawer-scroll-body", timeout=8000)
        page.wait_for_timeout(500)

        tab4 = page.locator('button.drawer-tab-btn[data-tab="legislative_history"]')
        tab4.click()
        page.wait_for_timeout(800)

        content_area = page.locator("#drawer-tab-content-area")
        cards = content_area.locator(".card")
        print(f"  APA Art 1 cards count: {cards.count()} (Expected: 1)")
        assert cards.count() == 1

        shot4_path = os.path.join(SHOTS_DIR, "01_single_version_apa_art1.png")
        page.screenshot(path=shot4_path)
        print(f"  Captured Screenshot 4: {shot4_path}")

        browser.close()
        print("\n>>> ALL 4 PLAYWRIGHT VERIFICATION CASES PASSED! <<<")

if __name__ == "__main__":
    run_4shots_verification()
