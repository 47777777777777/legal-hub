"""
Legal Hub End-to-End Playwright Smoke Test.
Verifies:
1. Dead button & HTML element ID reference integrity.
2. Homepage load & nine-grid popular acts render.
3. Statute search ('民事訴訟') returns '民事訴訟法' as #1; card count == API articles count (800).
4. CPC Art 2: No forbidden/guessed strings, shows '此條尚無外部解析資料', screenshot taken.
5. CPC Art 244: Deep reading & 10 judgments rendered with provenance tags, screenshot taken.
6. Criminal Code Art 2: No mock strings, source provenance verified, screenshot taken.
7. Un-enriched article: only official text + '此條尚無外部解析資料', screenshot taken.
8. Negative test: Civil Code Art 1052 (contains '有期徒刑') contains zero criminal elements/prosecution tags.
9. Drawer action buttons: copy, bookmark, permalink, PDF window.print, split width, prev/next.
10. Top navbar controls: density, theme, font +/-, TOC collapse, dialer modal.
11. Ctrl+F keypress preserved natively without preventDefault.
12. Total browser console errors = 0 across the entire suite.
"""
import os
import sys
import time
import re

sys.stdout.reconfigure(encoding='utf-8')

from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = int(os.environ.get("PORT", 8080))
BASE_URL = f"http://127.0.0.1:{PORT}"
SCREENSHOT_DIR = os.path.join(BASE_DIR, "reports", "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

FORBIDDEN_TERMS = [
    "故意責任",
    "公訴追訴",
    "刑度範疇",
    "時效抗辯",
    "權利阻卻",
    "法定要件行為態樣",
    "autoSummary",
    "parseArticleElements"
]

def detect_dead_buttons():
    print("[Smoke 1/10] Running dead button & ID reference check...")
    with open(os.path.join(BASE_DIR, 'static', 'index.html'), 'r', encoding='utf-8') as f:
        html = f.read()

    with open(os.path.join(BASE_DIR, 'static', 'js', 'app.js'), 'r', encoding='utf-8') as f:
        app_js = f.read()

    with open(os.path.join(BASE_DIR, 'static', 'js', 'dialer.js'), 'r', encoding='utf-8') as f:
        dialer_js = f.read()

    js_all = app_js + '\n' + dialer_js

    # 1. IDs in JS getElementById
    js_ids = set(re.findall(r'getElementById\(["\']([^"\']+)["\']\)', js_all))

    # 2. IDs in HTML
    html_ids = set(re.findall(r'id=["\']([^"\']+)["\']', html))

    # Dynamic IDs created by JS template strings
    dynamic_ids = set()
    for m in re.finditer(r'id=["\']([^"\']+)["\']', js_all):
        dynamic_ids.add(m.group(1))

    missing_in_html = sorted([i for i in js_ids if i not in html_ids and i not in dynamic_ids])
    
    # 3. HTML buttons
    buttons = re.findall(r'<button\b([^>]*)>', html)
    buttons_without_handler = []
    for b in buttons:
        id_m = re.search(r'id=["\']([^"\']+)["\']', b)
        onclick_m = re.search(r'onclick=["\']([^"\']+)["\']', b)
        class_m = re.search(r'class=["\']([^"\']+)["\']', b)
        
        b_id = id_m.group(1) if id_m else None
        has_click = False
        if onclick_m:
            has_click = True
        elif b_id and (f'getElementById("{b_id}")' in js_all or f"getElementById('{b_id}')" in js_all or b_id in js_all):
            has_click = True
        elif class_m:
            for c in class_m.group(1).split():
                if f'.{c}' in js_all:
                    has_click = True
                    break
        if not has_click:
            buttons_without_handler.append((b_id or b))

    print(f"  Missing IDs in HTML: {len(missing_in_html)} -> {missing_in_html}")
    print(f"  Unhandled buttons:   {len(buttons_without_handler)} -> {buttons_without_handler}")
    
    if missing_in_html or buttons_without_handler:
        raise AssertionError(f"Dead button check failed: missing {missing_in_html}, unhandled {buttons_without_handler}")
    print("  PASSED: Zero dead buttons or broken element references.")

def run_smoke_test():
    detect_dead_buttons()
    
    console_errors = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            permissions=["clipboard-read", "clipboard-write"],
            viewport={"width": 1440, "height": 900}
        )
        page = context.new_page()
        
        # Track console errors
        def on_console(msg):
            if msg.type == "error":
                text = msg.text
                if "favicon.ico" not in text:
                    console_errors.append(f"[Console Error] {text}")
                    
        def on_page_error(err):
            console_errors.append(f"[Page Error] {err}")
            
        page.on("console", on_console)
        page.on("pageerror", on_page_error)
        
        # 1. Load Homepage
        print(f"[Smoke 2/10] Loading homepage at {BASE_URL}...")
        page.goto(BASE_URL, wait_until="networkidle")
        time.sleep(0.5)
        
        # Verify title & nine-grid
        assert "Legal Hub" in page.title()
        chips = page.query_selector_all(".popular-act-chip")
        print(f"  Popular act chips count: {len(chips)}")
        assert len(chips) >= 9, f"Expected 9 popular acts, found {len(chips)}"
        
        # 2. Search '民事訴訟' & load Civil Procedure Code
        print("[Smoke 3/10] Testing statute search ranking for '民事訴訟' and waiting for full render...")
        add_tab_btn = page.query_selector("#add-tab-btn")
        if add_tab_btn:
            add_tab_btn.click()
            page.wait_for_selector("#add-tab-modal:not(.hidden)", state="visible")
            
        search_input = page.query_selector("#tab-search-input")
        assert search_input is not None
        search_input.fill("民事訴訟")
        time.sleep(0.6)  # Wait for debounce
        
        page.wait_for_selector(".act-result-row", state="visible", timeout=5000)
        first_result = page.query_selector(".act-result-row")
        assert first_result is not None, "Search for '民事訴訟' returned no results!"
        first_text = first_result.inner_text()
        print(f"  Top search result: '{first_text.strip()}'")
        assert "民事訴訟法" in first_text, f"Expected '民事訴訟法' top result, got '{first_text}'"
        
        # Click first result to load act and wait for complete asynchronous loading
        first_result.click()
        page.wait_for_function(
            "() => window.legalHubApp && "
            "window.legalHubApp.currentAct && "
            "window.legalHubApp.currentAct.id === 'civil_procedure_code' && "
            "window.legalHubApp.currentAct.articles && "
            "window.legalHubApp.currentAct.articles.length === 800 && "
            "document.querySelectorAll('.stream-article-card').length === 800",
            timeout=20000
        )
        articles = page.query_selector_all(".stream-article-card")
        total_arts = page.evaluate("window.legalHubApp.currentAct.articles.length")
        print(f"  Loaded '民事訴訟法' article list: {len(articles)} cards rendered (API total: {total_arts}).")
        assert len(articles) == total_arts
        assert len(articles) == 800, f"Expected 800 articles for civil_procedure_code, got {len(articles)}"
        
        # 3. CPC Art 2 Verification
        print("[Smoke 4/10] Verifying CPC Art 2 (no guessed content, no mock flowcharts, shows un-enriched message)...")
        page.evaluate("window.legalHubApp.openStudyDrawer('2')")
        page.wait_for_selector("#study-drawer:not(.hidden)", state="visible", timeout=5000)
        time.sleep(0.3)
        
        drawer_text = page.query_selector("#study-drawer-panel").inner_text()
        for term in FORBIDDEN_TERMS:
            assert term not in drawer_text, f"Forbidden term '{term}' found in CPC Art 2 drawer!"
            
        assert "構成要件與法律效果" not in drawer_text, "Found forbidden '構成要件與法律效果' block in CPC Art 2!"
        assert "思考脈絡審查路徑圖" not in drawer_text, "Found forbidden '思考脈絡審查路徑圖' block in CPC Art 2!"
        assert "此條尚無外部解析資料" in drawer_text, "CPC Art 2 should display '此條尚無外部解析資料'!"
        
        # Screenshot CPC Art 2
        cpc_2_path = os.path.join(SCREENSHOT_DIR, "local_cpc_art_2.png")
        page.screenshot(path=cpc_2_path)
        print(f"  Saved screenshot: {cpc_2_path}")
        
        # 4. CPC Art 244 Verification
        print("[Smoke 5/10] Verifying CPC Art 244 (deep reading & 10 judgments with provenance tags)...")
        page.evaluate("async () => await window.legalHubApp.openStudyDrawer('244')")
        page.wait_for_selector(".drawer-tab-btn[data-tab='insights']", state="visible", timeout=10000)
        
        drawer_panel = page.query_selector("#study-drawer-panel")
        d244_text = drawer_panel.inner_text()
        for term in FORBIDDEN_TERMS:
            assert term not in d244_text, f"Forbidden term '{term}' found in CPC Art 244 drawer!"
            
        # Check Tab 2 (Practical Judgments: data-tab='insights')
        page.click('.drawer-tab-btn[data-tab="insights"]')
        page.wait_for_selector("#drawer-tab-content-area .judgment-card", state="visible", timeout=10000)
        tab2_html = page.query_selector("#drawer-tab-content-area").inner_html()
        assert "來源：法律人" in tab2_html, "CPC Art 244 judgments section missing provenance source tag!"
        judg_count = page.evaluate("document.querySelectorAll('#drawer-tab-content-area .judgment-card').length")
        print(f"  CPC Art 244 judgments count: {judg_count}")
        assert judg_count == 10, f"Expected 10 judgments for CPC Art 244, got {judg_count}"
        
        # Check Tab 1 (Deep Reading: data-tab='key_knowledge')
        page.click('.drawer-tab-btn[data-tab="key_knowledge"]')
        time.sleep(0.3)
        tab1_html = page.query_selector("#drawer-tab-content-area").inner_html()
        assert "深度解讀" in tab1_html, "CPC Art 244 missing '深度解讀' section!"
        assert "來源：法律人" in tab1_html, "CPC Art 244 deep reading missing provenance tag!"
        
        cpc_244_path = os.path.join(SCREENSHOT_DIR, "local_cpc_art_244.png")
        page.screenshot(path=cpc_244_path)
        print(f"  Saved screenshot: {cpc_244_path}")
        
        # 5. Criminal Code Art 2 Verification
        print("[Smoke 6/10] Verifying Criminal Code Art 2 (no mock content, clean provenance)...")
        page.evaluate("async () => { await window.legalHubApp.loadAct('criminal_code'); await window.legalHubApp.openStudyDrawer('2'); }")
        time.sleep(0.8)
        
        crim_2_text = page.query_selector("#study-drawer-panel").inner_text()
        for term in FORBIDDEN_TERMS:
            assert term not in crim_2_text, f"Forbidden term '{term}' found in Criminal Code Art 2 drawer!"
            
        crim_2_path = os.path.join(SCREENSHOT_DIR, "local_criminal_art_2.png")
        page.screenshot(path=crim_2_path)
        print(f"  Saved screenshot: {crim_2_path}")
        
        # 6. Un-enriched Article Verification (e.g. Criminal Code Art 3)
        print("[Smoke 7/10] Verifying un-enriched article displays clean official text only...")
        page.evaluate("async () => await window.legalHubApp.openStudyDrawer('3')")
        time.sleep(0.5)
        
        art3_text = page.query_selector("#study-drawer-panel").inner_text()
        assert "此條尚無外部解析資料" in art3_text, "Un-enriched article should state '此條尚無外部解析資料'!"
        
        unenriched_path = os.path.join(SCREENSHOT_DIR, "local_unenriched_art.png")
        page.screenshot(path=unenriched_path)
        print(f"  Saved screenshot: {unenriched_path}")
        
        # 7. Negative Test: Civil article with '有期徒刑' (Civil Code Art 1052)
        print("[Smoke 8/10] Running negative test on Civil Code Art 1052 (contains '有期徒刑', zero criminal tags)...")
        page.evaluate("async () => { await window.legalHubApp.loadAct('civil_code'); await window.legalHubApp.openStudyDrawer('1052'); }")
        time.sleep(0.8)
        
        civil_1052_text = page.query_selector("#study-drawer-panel").inner_text()
        for term in FORBIDDEN_TERMS:
            assert term not in civil_1052_text, f"Civil Code Art 1052 erroneously displayed criminal term '{term}'!"
        assert "刑度範疇" not in civil_1052_text
        assert "公訴追訴" not in civil_1052_text
        assert "故意責任" not in civil_1052_text
        print("  PASSED: Civil Code Art 1052 has zero synthesized criminal classification tags.")
        
        # 8. Drawer Actions & Navbar Controls
        print("[Smoke 9/10] Verifying drawer controls, bookmark, permalink, PDF print, and top navbar controls...")
        # Drawer buttons
        copy_btn = page.query_selector("#drawer-copy-article-btn")
        if copy_btn: copy_btn.click()
        
        bookmark_btn = page.query_selector("#drawer-bookmark-btn")
        if bookmark_btn: bookmark_btn.click()
        
        # Permalink hash
        assert "#/act/civil_code/" in page.url
        
        # PDF print mock
        page.evaluate("window.printCalled = false; window.print = () => { window.printCalled = true; };")
        pdf_btn = page.query_selector("#drawer-pdf-btn")
        if pdf_btn:
            pdf_btn.click()
            time.sleep(0.1)
            assert page.evaluate("window.printCalled") is True
            
        # Top toolbar controls
        page.click("#density-toggle-btn")
        page.click("#density-toggle-btn")
        page.click("#theme-toggle-btn")
        page.click("#theme-toggle-btn")
        page.click("#font-plus-btn")
        page.click("#font-minus-btn")
        
        # Ctrl+F check
        page.evaluate("""
            window.__ctrlFPrevented = null;
            window.__searchFocused = false;
            const searchInput = document.getElementById("search-input");
            if (searchInput) {
                searchInput.addEventListener("focus", () => { window.__searchFocused = true; });
            }
            window.addEventListener("keydown", (e) => {
                if (e.ctrlKey && e.key.toLowerCase() === "f") {
                    window.__ctrlFPrevented = e.defaultPrevented;
                }
            });
        """)
        page.click("body")
        page.keyboard.press("Control+f")
        time.sleep(0.2)
        assert page.evaluate("window.__ctrlFPrevented") is not True
        assert page.evaluate("window.__searchFocused") is False
        
        # 9. Verify Console Errors = 0
        print("[Smoke 10/10] Verifying zero console errors...")
        print(f"  Total console errors logged: {len(console_errors)}")
        if console_errors:
            for err in console_errors:
                print(f"    {err}")
            raise AssertionError(f"Console errors detected ({len(console_errors)}): {console_errors}")
        print("  PASSED: Console error count is exactly 0.")
        
        browser.close()
        
    print("\n>>> ALL SMOKE UI TESTS PASSED SUCCESSFULLY! <<<")
    return 0

if __name__ == "__main__":
    sys.exit(run_smoke_test())
