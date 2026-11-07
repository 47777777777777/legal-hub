import os
import sys
import json
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

def test_single_art_fetch():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent="LegalHubPersonal/1.0")
        
        # Step 1: Search portal
        page.goto("https://lis.ly.gov.tw/lglawc/lglawkm", wait_until="domcontentloaded")
        page.fill("input[name='_1_6_T']", "行政程序法")
        page.click("input[name='_IMG_檢索']")
        page.wait_for_timeout(1500)
        
        # Step 2: Act entry link
        url2 = page.evaluate("""() => {
            const a = Array.from(document.querySelectorAll('a')).find(x => x.innerText.trim() === '行政程序法' && x.href.includes('lawsingle'));
            return a ? a.href : null;
        }""")
        page.goto(url2, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)

        # Get base prefix
        base_url = page.url
        print(f"Base act URL: {base_url}")
        
        # Now let's try opening single article for Art 1, Art 128, Art 174-1
        # Click yellow_btn01 (單條檢視)
        single_btn = page.query_selector("img[src*='yellow_btn01']")
        if single_btn:
            parent_a = single_btn.evaluate_handle("el => el.closest('a')")
            parent_a.click()
            page.wait_for_timeout(1500)
            print(f"Single article view URL: {page.url}")
            print(f"Title: {page.title()}")
            content = page.content()
            print("Content has 第一條:", "第一條" in content)
            print("Content has 理由:", "理由" in content)

        browser.close()

if __name__ == "__main__":
    test_single_art_fetch()

