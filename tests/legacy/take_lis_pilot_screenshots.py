import os
import time
from playwright.sync_api import sync_playwright

OUT_DIR = os.path.join("reports", "screenshots", "lis_pilot")
os.makedirs(OUT_DIR, exist_ok=True)

def take_screenshots():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        
        # 1. Open app
        print("Navigating to http://127.0.0.1:8080...")
        page.goto("http://127.0.0.1:8080", wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        
        # Switch to admin_procedure_act
        page.evaluate("() => window.legalHubApp.openResearchTab('admin_procedure_act', '行政程序法')")
        page.wait_for_timeout(2000)

        # Shot 1: Article 128 (has reasons + comparison table)
        print("Loading Article 128...")
        page.evaluate("() => window.legalHubApp.openStudyDrawer('128')")
        page.wait_for_selector("#study-drawer:not(.hidden)", state="visible", timeout=5000)
        page.wait_for_timeout(500)
        # Click Legislative Reasons Tab (legislative_history)
        page.click("button.drawer-tab-btn[data-tab='legislative_history']")
        page.wait_for_timeout(1000)
        shot1 = os.path.join(OUT_DIR, "pilot_art_128_comparison_reasons.png")
        page.screenshot(path=shot1, full_page=False)
        print(f"Saved: {shot1}")

        # Shot 2: Article 1 (has original enactment reason)
        print("Loading Article 1...")
        page.evaluate("() => window.legalHubApp.openStudyDrawer('1')")
        page.wait_for_timeout(1000)
        page.click("button.drawer-tab-btn[data-tab='legislative_history']")
        page.wait_for_timeout(1000)
        shot2 = os.path.join(OUT_DIR, "pilot_art_1_reasons.png")
        page.screenshot(path=shot2, full_page=False)
        print(f"Saved: {shot2}")

        # Shot 3: Article 174-1 (has multiple revision reasons)
        print("Loading Article 174-1...")
        page.evaluate("() => window.legalHubApp.openStudyDrawer('174-1')")
        page.wait_for_timeout(1000)
        page.click("button.drawer-tab-btn[data-tab='legislative_history']")
        page.wait_for_timeout(1000)
        shot3 = os.path.join(OUT_DIR, "pilot_art_174_1_reasons.png")
        page.screenshot(path=shot3, full_page=False)
        print(f"Saved: {shot3}")

        # Shot 4: Article 2 (no LIS reasons seeded yet, shows standard notice)
        print("Loading Article 2...")
        page.evaluate("() => window.legalHubApp.openStudyDrawer('2')")
        page.wait_for_timeout(1000)
        page.click("button.drawer-tab-btn[data-tab='legislative_history']")
        page.wait_for_timeout(1000)
        shot4 = os.path.join(OUT_DIR, "pilot_art_2_no_data.png")
        page.screenshot(path=shot4, full_page=False)
        print(f"Saved: {shot4}")

        browser.close()
        print("All screenshots taken successfully!")

if __name__ == "__main__":
    take_screenshots()
