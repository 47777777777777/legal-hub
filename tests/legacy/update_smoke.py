with open('scripts/smoke_ui.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_block = '''        # 4. CPC Art 244 Verification
        print("[Smoke 5/10] Verifying CPC Art 244 (deep reading & 10 judgments with provenance tags)...")
        page.evaluate("window.legalHubApp.openStudyDrawer('244')")
        time.sleep(0.5)
        
        drawer_panel = page.query_selector("#study-drawer-panel")
        d244_text = drawer_panel.inner_text()
        for term in FORBIDDEN_TERMS:
            assert term not in d244_text, f"Forbidden term '{term}' found in CPC Art 244 drawer!"
            
        # Check Tab 2 (Practical Judgments)
        page.click('.drawer-tab-btn[data-tab="practical"]')
        time.sleep(0.3)
        tab2_html = page.query_selector("#drawer-tab-content-area").inner_html()
        assert "來源：法律人" in tab2_html, "CPC Art 244 judgments section missing provenance source tag!"
        judg_count = page.evaluate("document.querySelectorAll('#drawer-tab-content-area .judgment-card').length")
        print(f"  CPC Art 244 judgments count: {judg_count}")
        assert judg_count == 10, f"Expected 10 judgments for CPC Art 244, got {judg_count}"
        
        # Check Tab 1 (Deep Reading)
        page.click('.drawer-tab-btn[data-tab="summary"]')
        time.sleep(0.3)
        tab1_html = page.query_selector("#drawer-tab-content-area").inner_html()
        assert "深度解讀" in tab1_html, "CPC Art 244 missing '深度解讀' section!"
        assert "來源：法律人" in tab1_html, "CPC Art 244 deep reading missing provenance tag!"
        
        cpc_244_path = os.path.join(SCREENSHOT_DIR, "local_cpc_art_244.png")
        page.screenshot(path=cpc_244_path)
        print(f"  Saved screenshot: {cpc_244_path}")
        
        # 5. Criminal Code Art 2 Verification
        print("[Smoke 6/10] Verifying Criminal Code Art 2 (no mock content, clean provenance)...")
        page.evaluate("window.legalHubApp.loadAct('criminal_code').then(() => window.legalHubApp.openStudyDrawer('2'))")
        time.sleep(0.8)
        
        crim_2_text = page.query_selector("#study-drawer-panel").inner_text()
        for term in FORBIDDEN_TERMS:
            assert term not in crim_2_text, f"Forbidden term '{term}' found in Criminal Code Art 2 drawer!"
            
        crim_2_path = os.path.join(SCREENSHOT_DIR, "local_criminal_art_2.png")
        page.screenshot(path=crim_2_path)
        print(f"  Saved screenshot: {crim_2_path}")
        
        # 6. Un-enriched Article Verification (e.g. Criminal Code Art 3 or Constitution Art 1)
        print("[Smoke 7/10] Verifying un-enriched article displays clean official text only...")
        page.evaluate("window.legalHubApp.openStudyDrawer('3')")
        time.sleep(0.5)
        
        art3_text = page.query_selector("#study-drawer-panel").inner_text()
        assert "此條尚無外部解析資料" in art3_text, "Un-enriched article should state '此條尚無外部解析資料'!"
        
        unenriched_path = os.path.join(SCREENSHOT_DIR, "local_unenriched_art.png")
        page.screenshot(path=unenriched_path)
        print(f"  Saved screenshot: {unenriched_path}")
        
        # 7. Negative Test: Civil article with '有期徒刑' (Civil Code Art 1052)
        print("[Smoke 8/10] Running negative test on Civil Code Art 1052 (contains '有期徒刑', zero criminal tags)...")
        page.evaluate("window.legalHubApp.loadAct('civil_code').then(() => window.legalHubApp.openStudyDrawer('1052'))")
        time.sleep(0.8)'''

new_block = '''        # 4. CPC Art 244 Verification
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
        time.sleep(0.8)'''

if old_block in text:
    text = text.replace(old_block, new_block)
    with open('scripts/smoke_ui.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print('Updated smoke_ui.py cleanly')
else:
    print('old_block not found in smoke_ui.py')

