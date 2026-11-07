import sys
import time
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto("http://127.0.0.1:8080", wait_until="networkidle")
    
    print("Loading civil_procedure_code...")
    page.evaluate("async () => await window.legalHubApp.loadAct('civil_procedure_code')")
    time.sleep(0.5)
    
    print("Opening CPC Art 244 drawer...")
    page.evaluate("async () => await window.legalHubApp.openStudyDrawer('244')")
    page.wait_for_selector(".drawer-tab-btn[data-tab='insights']", state="visible", timeout=10000)
    print("Found insights tab!")
    
    page.click(".drawer-tab-btn[data-tab='insights']")
    time.sleep(0.3)
    
    html = page.query_selector("#drawer-tab-content-area").inner_html()
    print("Has source tag:", "來源：法律人" in html)
    
    judg_count = page.evaluate("document.querySelectorAll('#drawer-tab-content-area .judgment-card').length")
    print("Judgments count:", judg_count)
    
    page.click(".drawer-tab-btn[data-tab='key_knowledge']")
    time.sleep(0.3)
    s_html = page.query_selector("#drawer-tab-content-area").inner_html()
    print("Has deep reading:", "深度解讀" in s_html)
    print("Deep reading has source tag:", "來源：法律人" in s_html)
    
    browser.close()
    print("Test drawer flow SUCCESS!")
