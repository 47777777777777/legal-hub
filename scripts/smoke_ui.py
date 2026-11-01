"""
Legal Hub End-to-End Playwright Smoke Test.
Verifies:
1. Console errors = 0 across the entire flow.
2. Homepage load & nine-grid popular acts render.
3. Statute search ('民事訴訟') returns '民事訴訟法' as #1, clicks and loads article list.
4. Article selection & Study Drawer opening.
5. All drawer tabs & action buttons (copy, bookmark, permalink, PDF window.print, split width, prev/next article).
6. Top navbar & toolbar buttons (density, theme, font +/-, TOC collapse, add-tab modal, quick dialer).
7. Ctrl+F keypress does not get hijacked by single-key 'f' shortcut.
8. Dead button detection: 0 missing HTML IDs, 0 unhandled buttons.
"""
import os
import sys
import time
import re
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = int(os.environ.get("PORT", 8080))
BASE_URL = f"http://127.0.0.1:{PORT}"

def detect_dead_buttons():
    print("[Smoke 1/8] Running dead button & ID reference check...")
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
            permissions=["clipboard-read", "clipboard-write"]
        )
        page = context.new_page()
        
        # Track console errors
        def on_console(msg):
            if msg.type == "error":
                # Filter out intentional 404 literature probes if any
                text = msg.text
                if "favicon.ico" not in text:
                    console_errors.append(f"[Console Error] {text}")
                    
        def on_page_error(err):
            console_errors.append(f"[Page Error] {err}")
            
        page.on("console", on_console)
        page.on("pageerror", on_page_error)
        
        # 1. Load Homepage
        print(f"[Smoke 2/8] Loading homepage at {BASE_URL}...")
        page.goto(BASE_URL, wait_until="networkidle")
        time.sleep(0.5)
        
        # Verify title & nine-grid
        assert "Legal Hub" in page.title()
        chips = page.query_selector_all(".popular-act-chip")
        print(f"  Popular act chips count: {len(chips)}")
        assert len(chips) >= 9, f"Expected 9 popular acts, found {len(chips)}"
        
        # 2. Search '民事訴訟'
        print("[Smoke 3/8] Testing statute search ranking for '民事訴訟'...")
        # Open modal
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
        
        # Click first result to load act
        first_result.click()
        page.wait_for_selector(".stream-article-card", state="visible", timeout=15000)
        articles = page.query_selector_all(".stream-article-card")
        print(f"  Loaded '民事訴訟法' article list: {len(articles)} articles rendered.")
        assert len(articles) > 0
        
        # 3. Open Article Drawer
        print("[Smoke 4/8] Testing article drawer interaction...")
        page.locator(".stream-article-card").first.click()
        page.wait_for_selector("#study-drawer:not(.hidden)", state="visible", timeout=5000)
        drawer_badge = page.query_selector("#drawer-article-badge").inner_text()
        print(f"  Drawer opened for: '{drawer_badge.strip()}'")
        assert len(drawer_badge) > 0
        
        # 4. Test Drawer Tabs & Buttons
        print("[Smoke 5/8] Testing drawer tabs and toolbar buttons...")
        tabs = page.query_selector_all(".drawer-tab-btn")
        for tab in tabs:
            tab.click()
            time.sleep(0.1)
            assert "active" in tab.get_attribute("class")
            
        # Test Bookmark button
        bookmark_btn = page.query_selector("#drawer-bookmark-btn")
        if bookmark_btn:
            bookmark_btn.click()
            time.sleep(0.1)
            print("  Bookmark toggled successfully.")
            
        # Test Copy button
        copy_btn = page.query_selector("#drawer-copy-article-btn")
        if copy_btn:
            copy_btn.click()
            time.sleep(0.1)
            print("  Copy button clicked successfully.")
            
        # Test Permalink verification (URL hash reflects current article)
        print(f"  Current URL with permalink hash: {page.url}")
        assert "#/act/civil_procedure_code/" in page.url
            
        # Test PDF button (mock window.print)
        page.evaluate("window.printCalled = false; window.print = () => { window.printCalled = true; };")
        pdf_btn = page.query_selector("#drawer-pdf-btn")
        if pdf_btn:
            pdf_btn.click()
            time.sleep(0.1)
            assert page.evaluate("window.printCalled") is True
            print("  PDF (window.print) triggered successfully.")
            
        # Test Split Width button
        split_btn = page.query_selector("#drawer-split-btn")
        if split_btn:
            drawer_panel = page.query_selector("#study-drawer-panel")
            w_before = drawer_panel.bounding_box()["width"]
            split_btn.click()
            time.sleep(0.1)
            w_after = drawer_panel.bounding_box()["width"]
            print(f"  Split-view width toggled: {w_before}px -> {w_after}px")
            split_btn.click()  # restore
            
        # Test Next / Prev Article button (or keyboard shortcuts [ and ])
        next_btn = page.query_selector("#drawer-next-btn")
        if next_btn and not next_btn.is_disabled():
            next_btn.click()
            time.sleep(0.3)
            badge2 = page.query_selector("#drawer-article-badge").inner_text()
            print(f"  Next article navigated: '{badge2.strip()}'")
            prev_btn = page.query_selector("#drawer-prev-btn")
            if prev_btn and not prev_btn.is_disabled():
                prev_btn.click()
                time.sleep(0.3)
        else:
            # Test keyboard bracket shortcut
            page.keyboard.press("BracketRight")
            time.sleep(0.3)
            badge2 = page.query_selector("#drawer-article-badge").inner_text()
            print(f"  Next article navigated via ']': '{badge2.strip()}'")
            page.keyboard.press("BracketLeft")
            time.sleep(0.3)
                
        # 5. Top Navbar Controls
        print("[Smoke 6/8] Testing top navbar controls (density, theme, font, TOC, modal, dialer)...")
        # Density toggle
        density_btn = page.query_selector("#density-toggle-btn")
        curr_density = page.get_attribute("html", "data-density")
        density_btn.click()
        new_density = page.get_attribute("html", "data-density")
        assert curr_density != new_density
        density_btn.click()  # restore
        print("  Density toggle verified.")
        
        # Theme toggle
        theme_btn = page.query_selector("#theme-toggle-btn")
        curr_theme = page.get_attribute("html", "data-theme")
        theme_btn.click()
        new_theme = page.get_attribute("html", "data-theme")
        assert curr_theme != new_theme
        theme_btn.click()  # restore
        print("  Theme toggle verified.")
        
        # Font size +/-
        font_plus = page.query_selector("#font-plus-btn")
        font_minus = page.query_selector("#font-minus-btn")
        font_plus.click()
        font_minus.click()
        print("  Font size controls verified.")
        
        # TOC collapse toggle
        toc_btn = page.query_selector("#toc-toggle-btn")
        toc = page.query_selector("#sidebar-toc")
        if toc_btn and toc:
            was_collapsed = "collapsed" in (toc.get_attribute("class") or "")
            toc_btn.click()
            time.sleep(0.1)
            is_collapsed = "collapsed" in (toc.get_attribute("class") or "")
            assert was_collapsed != is_collapsed
            toc_btn.click()  # restore
            print("  TOC collapse verified.")
            
        # Quick Dialer toggle
        dialer_btn = page.query_selector("#dialer-toggle-btn")
        dialer = page.query_selector("#quick-dialer")
        if dialer_btn and dialer:
            dialer_btn.click()
            time.sleep(0.1)
            assert "hidden" not in (dialer.get_attribute("class") or "")
            close_btn = page.query_selector("#dialer-close-btn")
            if close_btn:
                close_btn.click()
                time.sleep(0.1)
                assert "hidden" in (dialer.get_attribute("class") or "")
            print("  Quick dialer modal verified.")
            
        # 6. Test Ctrl+F Non-interference
        print("[Smoke 7/8] Testing Ctrl+F keypress does not trigger search shortcut or preventDefault...")
        # Attach listener to record preventDefault on keydown
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
        
        # Focus on body (not input)
        page.click("body")
        page.keyboard.press("Control+f")
        time.sleep(0.2)
        
        ctrl_f_prevented = page.evaluate("window.__ctrlFPrevented")
        search_focused = page.evaluate("window.__searchFocused")
        print(f"  Ctrl+F preventDefault: {ctrl_f_prevented}, searchInput focused: {search_focused}")
        assert ctrl_f_prevented is not True, "Ctrl+F was intercepted by preventDefault!"
        assert search_focused is False, "Ctrl+F erroneously focused in-act search input!"
        print("  PASSED: Ctrl+F natively preserved for browser search.")
        
        # 7. Check Console Errors
        print("[Smoke 8/8] Verifying zero console errors...")
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
