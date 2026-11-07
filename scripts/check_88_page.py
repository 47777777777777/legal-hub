import sys
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(user_agent="LegalHubPersonal/1.0")
    page.goto("https://lis.ly.gov.tw/lglawc/lglawkm", wait_until="domcontentloaded")
    page.fill("input[name='_1_6_T']", "行政程序法")
    page.click("input[name='_IMG_檢索']")
    page.wait_for_timeout(1500)
    
    url2 = page.evaluate("""() => {
        const a = Array.from(document.querySelectorAll('a')).find(x => x.innerText.trim() === '行政程序法' && x.href.includes('lawsingle'));
        return a ? a.href : null;
    }""")
    page.goto(url2, wait_until="domcontentloaded")
    page.wait_for_timeout(1500)
    
    ver_88 = page.evaluate("""() => {
        const a = Array.from(document.querySelectorAll('a')).find(x => x.innerText.includes('88年1月15日'));
        return a ? a.href : null;
    }""")
    print("88 link:", ver_88)
    if ver_88:
        page.goto(ver_88, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        btn1_88 = page.evaluate("""() => {
            const a = document.querySelector('a img[src*="yellow_btn01"]');
            return a ? a.parentElement.href : null;
        }""")
        print("88 btn1 link:", btn1_88)
        if btn1_88:
            page.goto(btn1_88, wait_until="domcontentloaded")
            page.wait_for_timeout(1500)
            print("88 Reason page title:", page.title())
            text = page.locator("body").inner_text()
            print("88 Reason text length:", len(text))
            print("88 preview:\n", text[:400])
            print("Has 第一條:", "第一條" in text)
            print("Has 第一百七十五條:", "第一百七十五條" in text)
    browser.close()

