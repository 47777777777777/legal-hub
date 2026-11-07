import os
import sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

def test_ui():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        context.grant_permissions(["clipboard-read", "clipboard-write"])
        page = context.new_page()

        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))
        page.on("console", lambda msg: print(f"Console [{msg.type}]: {msg.text}") if msg.type == "error" else None)

        print("=== 1. Testing Non-Standard Act (動員戡亂時期臨時條款 A0000005) ===")
        page.goto("http://127.0.0.1:8080/#/act/a0000005", wait_until="networkidle")
        page.wait_for_selector(".stream-article-card", timeout=10000)

        # Check act meta
        meta_text = page.locator("#act-meta-inline").inner_text()
        print("Act meta inline:", meta_text)

        # Check cards
        cards = page.locator(".stream-article-card")
        count = cards.count()
        print(f"Rendered article cards count: {count}")

        # Check first card content (after foreword)
        card_0 = cards.nth(1) if count > 1 else cards.nth(0)
        text_0 = card_0.inner_text()
        print("First card text preview:\n", text_0[:160])

        assert "第 1 條" not in text_0, "Error: Found '第 1 條' in non-standard act card!"
        roman_spans = card_0.locator(".para-no")
        print(f"Roman numeral spans in first card: {roman_spans.count()}")
        assert roman_spans.count() == 0, "Error: Found Roman numeral in non-standard act!"

        os.makedirs("reports/screenshots", exist_ok=True)
        page.screenshot(path="reports/screenshots/a0000005.png", full_page=False)

        # Test Study Drawer on A0000005
        study_btn_0 = card_0.locator(".article-study-btn")
        study_btn_0.click()
        page.wait_for_selector("#study-drawer-scroll-body", timeout=5000)
        page.wait_for_timeout(500)

        # Copy mode plain on A0000005
        page.evaluate("document.getElementById('drawer-copy-plain-btn').click()")
        page.wait_for_timeout(300)
        copied_plain_a0005 = page.evaluate("navigator.clipboard.readText()")
        print("\n[A0000005 Copied Plain]:\n" + copied_plain_a0005[:200])

        # Copy mode roman on A0000005
        page.evaluate("document.getElementById('drawer-copy-roman-btn').click()")
        page.wait_for_timeout(300)
        copied_roman_a0005 = page.evaluate("navigator.clipboard.readText()")
        print("\n[A0000005 Copied Roman (Must have NO '第 1 條' and NO Roman numeral)]:\n" + copied_roman_a0005[:200])
        assert "第 1 條" not in copied_roman_a0005
        assert "Ⅰ" not in copied_roman_a0005

        print("\n=== 2. Testing Standard Multi-Paragraph Act (中華民國刑法 第 10 條) ===")
        page.goto("http://127.0.0.1:8080/#/act/criminal_code/article/10", wait_until="networkidle")
        page.wait_for_selector(".structure-block.has-roman", timeout=10000)
        page.wait_for_timeout(1000)

        card_10 = page.locator("#article-card-10")
        card_10_romans = card_10.locator(".para-no")
        print(f"Roman numerals in Article 10: {card_10_romans.count()} (Expected 8)")
        assert card_10_romans.count() >= 8

        # Color assertion
        color = card_10_romans.nth(0).evaluate("el => window.getComputedStyle(el).color")
        print("Roman numeral computed color:", color)
        assert "245, 158, 11" in color or "#f59e0b" in color, f"Expected gold, got {color}"

        # Visual alignment assertion
        blocks = card_10.locator(".structure-block.has-roman")
        x_coords = []
        for i in range(min(5, blocks.count())):
            body_el = blocks.nth(i).locator(".block-body")
            box = body_el.bounding_box()
            if box:
                x_coords.append(box["x"])
        print("X-coordinates of block-body:", x_coords)
        assert len(x_coords) > 1 and max(x_coords) - min(x_coords) < 1.0, f"Misaligned paragraph texts: {x_coords}"
        print("All paragraph bodies are perfectly aligned at x =", x_coords[0])

        page.screenshot(path="reports/screenshots/criminal_code_art10.png")

        # Open drawer and test 3 copy modes on Criminal Code Art 10
        card_10.locator(".article-study-btn").click()
        page.wait_for_selector("#study-drawer-scroll-body", timeout=5000)
        page.wait_for_timeout(500)

        page.evaluate("document.getElementById('drawer-copy-roman-btn').click()")
        page.wait_for_timeout(300)
        cc10_roman = page.evaluate("navigator.clipboard.readText()")
        print("\n[刑法第 10 條 Mode Roman Output]:\n" + cc10_roman[:300] + "...")
        assert "中華民國刑法 第 10 條" in cc10_roman
        assert "Ⅰ　稱以上、以下、以內者" in cc10_roman
        assert "Ⅱ　稱公務員者" in cc10_roman

        page.evaluate("document.getElementById('drawer-copy-label-btn').click()")
        page.wait_for_timeout(300)
        cc10_label = page.evaluate("navigator.clipboard.readText()")
        print("\n[刑法第 10 條 Mode Label Output]:\n" + cc10_label[:300] + "...")
        assert "第 1 項　稱以上、以下、以內者" in cc10_label
        assert "第 2 項　稱公務員者" in cc10_label

        page.evaluate("document.getElementById('drawer-copy-plain-btn').click()")
        page.wait_for_timeout(300)
        cc10_plain = page.evaluate("navigator.clipboard.readText()")
        print("\n[刑法第 10 條 Mode Plain Output]:\n" + cc10_plain[:200] + "...")

        print("\n=== 3. Testing Standard 2-Paragraph Act (民法 第 184 條) ===")
        page.goto("http://127.0.0.1:8080/#/act/civil_code/article/184", wait_until="networkidle")
        page.wait_for_selector(".structure-block.has-roman", timeout=10000)
        page.wait_for_timeout(1000)

        card_184 = page.locator("#article-card-184")
        card_184.locator(".article-study-btn").click()
        page.wait_for_selector("#study-drawer-scroll-body", timeout=5000)
        page.wait_for_timeout(500)

        page.evaluate("document.getElementById('drawer-copy-roman-btn').click()")
        page.wait_for_timeout(300)
        civ184_roman = page.evaluate("navigator.clipboard.readText()")
        print("\n[民法第 184 條 Mode Roman Output]:\n" + civ184_roman)
        assert "民法 第 184 條" in civ184_roman
        assert "Ⅰ　因故意或過失" in civ184_roman
        assert "Ⅱ　違反保護他人之法律" in civ184_roman

        page.screenshot(path="reports/screenshots/civil_code_art184.png")

        browser.close()
        print("\n>>> All Playwright UI & Clipboard Tests Passed 100%! <<<")

if __name__ == "__main__":
    test_ui()
