import time
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

def run_inspection():
    print("=== Launching Playwright Chromium E2E Inspection ===")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        console_logs = []
        network_errors = []

        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        page.on("requestfailed", lambda req: network_errors.append(f"FAILED: {req.method} {req.url} - {req.failure}"))

        target_url = "http://161.33.166.144"
        print(f"1. Navigating to {target_url}...")
        resp = page.goto(target_url, timeout=15000, wait_until="networkidle")
        print(f"   HTTP Status: {resp.status}")

        time.sleep(1)

        # Check title
        print(f"   Page Title: {page.title()}")

        # Check ccu-proxy-btn
        btn = page.query_selector("#ccu-proxy-btn")
        if not btn:
            print("❌ #ccu-proxy-btn NOT FOUND!")
            browser.close()
            return
        print("✓ Found #ccu-proxy-btn. Clicking to open modal...")
        btn.click()
        time.sleep(1)

        # Check modal visibility
        modal = page.query_selector("#ccu-modal")
        is_visible = modal and not ("hidden" in (modal.get_attribute("class") or ""))
        print(f"✓ Modal is visible: {is_visible}")

        # Check cache summary & status
        cache_summary = page.inner_text("#lit-stat-summary") if page.query_selector("#lit-stat-summary") else "N/A"
        harvest_status = page.inner_text("#harvest-status-text") if page.query_selector("#harvest-status-text") else "N/A"
        print(f"✓ Cache summary: {cache_summary}")
        print(f"✓ Harvest status: {harvest_status}")

        # Check search input & search for something
        print("2. Testing Search in modal...")
        search_input = page.query_selector("#ccu-search-input")
        search_btn = page.query_selector("#ccu-do-search-btn")
        if search_input and search_btn:
            search_input.fill("林山田")
            search_btn.click()
            time.sleep(1.5)
            results_text = page.inner_text("#ccu-search-results")
            print(f"   Search '林山田' result preview (first 250 chars):\n   {results_text[:250]}...")

        # Test clicking Start Harvest
        print("3. Testing Start Harvest button click...")
        start_btn = page.query_selector("#ccu-start-harvest-btn")
        if start_btn:
            print(f"   Start button text: '{start_btn.inner_text()}' | disabled: {start_btn.is_disabled()}")
            start_btn.click()
            time.sleep(2)
            terminal_text = page.inner_text("#harvest-terminal-logs") if page.query_selector("#harvest-terminal-logs") else "N/A"
            print(f"   Terminal log after click (last 300 chars):\n   {terminal_text[-300:]}")

        print("\n=== Console Logs captured during session ===")
        for log in console_logs[-15:]:
            print("  ", log)

        if network_errors:
            print("\n=== Network Errors ===")
            for err in network_errors:
                print("  ", err)
        else:
            print("\n✓ No network errors detected.")

        browser.close()
        print("=== E2E Inspection Finished ===")

if __name__ == "__main__":
    run_inspection()
