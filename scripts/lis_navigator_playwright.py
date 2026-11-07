import os
import sys
import json
from playwright.sync_api import sync_playwright

def inspect_search(law_name: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent="LegalHubPersonal/1.0")
        page.goto("https://lis.ly.gov.tw/lglawc/lglawkm", wait_until="domcontentloaded")
        page.wait_for_timeout(1000)

        page.fill("input[name='_1_6_T']", law_name)
        page.click("input[name='_IMG_檢索']")
        page.wait_for_timeout(2000)

        print(f"Landed on search results URL: {page.url}")

        links = page.evaluate("""() => {
            return Array.from(document.querySelectorAll('a')).map(a => ({
                text: a.innerText.trim(),
                href: a.href,
                img: Array.from(a.querySelectorAll('img')).map(i => i.src)
            }));
        }""")

        matching = [l for l in links if law_name in l['text'] or 'lawsingle' in l['href'] or '沿革' in l['text']]
        print(f"Total matching links: {len(matching)}")
        for m in matching:
            print("  ", m['text'], "->", m['href'])

        # Click first matching law link
        target_a = None
        for a in page.query_selector_all("a"):
            if a.inner_text().strip() == law_name:
                target_a = a
                break
        
        if target_a:
            print(f"\nClicking exact title '{law_name}'...")
            target_a.click()
            page.wait_for_timeout(2000)
            print(f"Landed on act view URL: {page.url}")

            # Now find '法條沿革'
            history_a = None
            for a in page.query_selector_all("a"):
                if "法條沿革" in a.inner_text():
                    history_a = a
                    break
            
            if history_a:
                href = history_a.get_attribute("href")
                full_history_url = page.evaluate(f"() => new URL('{href}', window.location.href).href")
                print(f"SUCCESS: Found '法條沿革' (全法逐條理由) URL: {full_history_url}")

                # Save the full page HTML
                history_a.click()
                page.wait_for_timeout(3000)
                print(f"Landed on Full Act Reason URL: {page.url}")
                full_html = page.content()
                print(f"HTML Length: {len(full_html)}")
                
                # Check for first article
                if "第一條" in full_html and "理由" in full_html:
                    print("VERIFIED: Full act page contains '第一條' and '理由'!")
            else:
                print("Could not find '法條沿革' button on act view.")

        browser.close()

if __name__ == "__main__":
    inspect_search("行政程序法")
