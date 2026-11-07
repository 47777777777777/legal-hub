import os
import sys
from playwright.sync_api import sync_playwright

def run_nav(law_name="行政程序法"):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent="LegalHubPersonal/1.0")
        
        # Step 1: Search portal
        page.goto("https://lis.ly.gov.tw/lglawc/lglawkm", wait_until="domcontentloaded")
        page.fill("input[name='_1_6_T']", law_name)
        page.click("input[name='_IMG_檢索']")
        page.wait_for_timeout(1500)
        
        # Step 2: Act entry link
        url2 = page.evaluate(f"""() => {{
            const a = Array.from(document.querySelectorAll('a')).find(x => x.innerText.trim() === '{law_name}' && x.href.includes('lawsingle'));
            return a ? a.href : null;
        }}""")
        print(f"Step 2: Law link -> {url2}")
        if not url2:
            print("Failed to find law link in search results.")
            browser.close()
            return
            
        page.goto(url2, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        
        # Step 3: Find '法條沿革' (Full act reasons)
        h_url = page.evaluate("""() => {
            const a = Array.from(document.querySelectorAll('a')).find(x => x.innerText.includes('法條沿革'));
            return a ? a.href : null;
        }""")
        print(f"Step 3: 法條沿革 link -> {h_url}")
        if not h_url:
            print("Failed to find 法條沿革 link.")
            browser.close()
            return

        page.goto(h_url, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        print(f"Step 4: Landed on Full Act Reasons Page: {page.url}")
        content = page.content()
        print(f"HTML Content-Length: {len(content)}")
        print("Verification in full act page:")
        print("  Has 第一條:", "第一條" in content)
        print("  Has 理由:", "理由" in content)
        print("  Has 第一百二十八條:", "第一百二十八條" in content)
        print("  Has 第一百七十四條:", "第一百七十四條" in content)
        
        browser.close()

if __name__ == "__main__":
    run_nav()

