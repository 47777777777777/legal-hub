with open("scripts/smoke_ui.py", "r", encoding="utf-8") as f:
    text = f.read()

# In Smoke 4/10:
# We should also verify CPC Art 2 Tab 2 (insights) and Tab 4 (legislative reasons):
# Check tab 4 shows "此條尚無立法理由資料"
# Check tab 2 shows "此條尚無實務見解資料"
target_s4 = """        drawer_text = page.query_selector("#study-drawer-panel").inner_text()
        for term in FORBIDDEN_TERMS:
            assert term not in drawer_text, f"Forbidden term '{term}' found in CPC Art 2 drawer!"
            
        assert "構成要件與法律效果" not in drawer_text, "Found forbidden '構成要件與法律效果' block in CPC Art 2!"
        assert "思考脈絡審查路徑圖" not in drawer_text, "Found forbidden '思考脈絡審查路徑圖' block in CPC Art 2!"
        assert "此條尚無外部解析資料" in drawer_text, "CPC Art 2 should display '此條尚無外部解析資料'!"
        
        # Screenshot CPC Art 2
        cpc_2_path = os.path.join(SCREENSHOT_DIR, f"{SCREENSHOT_PREFIX}cpc_art_2.png")
        page.screenshot(path=cpc_2_path)
        print(f"  Saved screenshot: {cpc_2_path}")"""

replacement_s4 = """        drawer_text = page.query_selector("#study-drawer-panel").inner_text()
        for term in FORBIDDEN_TERMS:
            assert term not in drawer_text, f"Forbidden term '{term}' found in CPC Art 2 drawer!"
            
        assert "構成要件與法律效果" not in drawer_text, "Found forbidden '構成要件與法律效果' block in CPC Art 2!"
        assert "思考脈絡審查路徑圖" not in drawer_text, "Found forbidden '思考脈絡審查路徑圖' block in CPC Art 2!"
        assert "現行明文規範" not in drawer_text, "Found forbidden '現行明文規範' block in CPC Art 2!"
        assert "最高法院" not in drawer_text, "Found forbidden '最高法院' fallback in CPC Art 2!"
        assert "法務部令函" not in drawer_text, "Found forbidden '法務部令函' fallback in CPC Art 2!"
        assert "此條尚無外部解析資料" in drawer_text, "CPC Art 2 Tab 1 should display '此條尚無外部解析資料'!"

        # Check Tab 2 (Insights) for CPC Art 2
        page.click('.drawer-tab-btn[data-tab="insights"]')
        time.sleep(0.3)
        tab2_cpc2_text = page.query_selector("#drawer-tab-content-area").inner_text()
        assert "此條尚無實務見解資料" in tab2_cpc2_text, "CPC Art 2 Tab 2 should display '此條尚無實務見解資料'!"

        # Check Tab 4 (Legislative Reasons) for CPC Art 2
        page.click('.drawer-tab-btn[data-tab="legislative"]')
        time.sleep(0.3)
        tab4_cpc2_text = page.query_selector("#drawer-tab-content-area").inner_text()
        assert "此條尚無立法理由資料" in tab4_cpc2_text, "CPC Art 2 Tab 4 should display '此條尚無立法理由資料'!"

        # Return to Tab 1
        page.click('.drawer-tab-btn[data-tab="key_knowledge"]')
        time.sleep(0.3)
        
        # Screenshot CPC Art 2
        cpc_2_path = os.path.join(SCREENSHOT_DIR, f"{SCREENSHOT_PREFIX}cpc_art_2.png")
        page.screenshot(path=cpc_2_path)
        print(f"  Saved screenshot: {cpc_2_path}")"""

assert target_s4 in text, "target_s4 not found in smoke_ui.py"
text = text.replace(target_s4, replacement_s4)

with open("scripts/smoke_ui.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Updated smoke_ui.py successfully!")

