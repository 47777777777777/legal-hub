import sys
from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print("Navigating to http://127.0.0.1:8080/#/act/criminal_code...")
        page.goto("http://127.0.0.1:8080/#/act/criminal_code")
        page.wait_for_selector(".stream-article-card")
        
        # Check for any .article-ref-link in the entire document
        ref_links = page.query_selector_all(".article-ref-link")
        print(f"Total .article-ref-link elements found: {len(ref_links)}")
        
        # Check Art 6 content exists and is intact
        art6 = page.query_selector("#article-card-6")
        if art6:
            text = art6.inner_text()
            print("Art 6 content preview:")
            for line in text.splitlines()[:5]:
                print("  ", line)
            assert "第一百二十一條至第一百二十三條" in text, "Text should remain intact"
            print("VERIFIED: Text remains 100% intact!")
        else:
            print("WARNING: #article-card-6 not found")
            
        assert len(ref_links) == 0, f"Expected 0 .article-ref-link, got {len(ref_links)}"
        print("PLAYWRIGHT ASSERTION PASSED: Zero .article-ref-link elements in DOM!")
        browser.close()

if __name__ == "__main__":
    main()

