import sys
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
    
    btn1 = page.evaluate("""() => {
        const a = document.querySelector('a img[src*="yellow_btn01"]');
        return a ? a.parentElement.href : null;
    }""")
    btn2 = page.evaluate("""() => {
        const a = document.querySelector('a img[src*="yellow_btn02"]');
        return a ? a.parentElement.href : null;
    }""")
    print("btn1 (yellow_btn01):", btn1)
    print("btn2 (yellow_btn02):", btn2)
    
    if btn1:
        p2 = browser.new_page(user_agent="LegalHubPersonal/1.0")
        p2.goto(btn1, wait_until="domcontentloaded")
        p2.wait_for_timeout(1500)
        print("Btn1 Page title:", p2.title())
        print("Btn1 Page text preview:")
        print(p2.locator("body").inner_text()[:300])
        p2.close()
        
    if btn2:
        p3 = browser.new_page(user_agent="LegalHubPersonal/1.0")
        p3.goto(btn2, wait_until="domcontentloaded")
        p3.wait_for_timeout(1500)
        print("Btn2 Page title:", p3.title())
        print("Btn2 Page text preview:")
        print(p3.locator("body").inner_text()[:300])
        p3.close()
        
    browser.close()

