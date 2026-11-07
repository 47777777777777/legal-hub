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
    
    link_128 = page.evaluate("""() => {
        const a = Array.from(document.querySelectorAll('a')).find(x => x.href.includes('012800'));
        return a ? a.href : null;
    }""")
    print("Visiting 128:", link_128)
    page.goto(link_128, wait_until="domcontentloaded")
    page.wait_for_timeout(1500)
    
    print("Body text:")
    print(page.locator("body").inner_text())
    
    links = page.evaluate("""() => Array.from(document.querySelectorAll('a')).map(x => ({text: x.innerText, href: x.href, img: x.querySelector('img') ? x.querySelector('img').src : null}))""")
    print("Links on Page 128:")
    for l in links:
        print(l)
    browser.close()

