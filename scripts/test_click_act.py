import sys
import time
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("http://127.0.0.1:8080", wait_until="networkidle")
    
    # Open modal
    page.click("#add-tab-btn")
    page.wait_for_selector("#add-tab-modal:not(.hidden)")
    
    # Fill search input
    page.fill("#tab-search-input", "民事訴訟")
    time.sleep(0.6)
    
    page.wait_for_selector(".act-result-row")
    row = page.query_selector(".act-result-row")
    print("Found row:", row.inner_text().strip().replace('\n', ' '))
    
    # Click row
    row.click()
    print("Clicked row")
    
    # Wait for act to load
    page.wait_for_function("() => window.legalHubApp && window.legalHubApp.currentAct && window.legalHubApp.currentAct.id === 'civil_procedure_code'", timeout=10000)
    print("currentAct.id loaded:", page.evaluate("window.legalHubApp.currentAct.id"))
    
    cards_count = page.evaluate("document.querySelectorAll('.stream-article-card').length")
    api_count = page.evaluate("window.legalHubApp.currentAct.articles.length")
    print(f"Cards count: {cards_count}, API articles count: {api_count}")
    
    browser.close()

