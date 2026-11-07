"""
scripts/test_search_lglawkm.py

Tests searching for statutes on LIS using Playwright.
"""
import os
import sys
import time
from playwright.sync_api import sync_playwright

USER_AGENT = "LegalHubPersonal/1.0"

def main():
    print("=== Testing Search on LIS (lis.ly.gov.tw) ===")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=USER_AGENT, viewport={"width": 1280, "height": 900})
        
        page.goto("https://lis.ly.gov.tw/lglawc/lglawkm", wait_until="domcontentloaded", timeout=15000)
        print("Page Title:", page.title())

        # Type statute name
        page.fill("input[name='_1_6_T']", "行政程序法")
        time.sleep(0.5)

        # Click search
        page.click("input[name='_IMG_檢索']")
        page.wait_for_load_state("domcontentloaded", timeout=15000)
        time.sleep(1.0)

        print("Search Results Page Title:", page.title())
        content = page.content()
        with open("data/raw/lis/samples/search_result_apa.html", "w", encoding="utf-8") as f:
            f.write(content)
        print("Saved search result to data/raw/lis/samples/search_result_apa.html")

        # Find links
        links = page.query_selector_all("a")
        print(f"Total links on search result: {len(links)}")
        for a in links:
            txt = a.inner_text().strip()
            href = a.get_attribute("href") or ""
            if "行政程序法" in txt or "lawsingle" in href or "lglaw" in href:
                print(f"  Result Link: [{txt}] -> {href}")

        browser.close()

if __name__ == "__main__":
    main()

