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
    
    # Click 條次
    link_tc = page.evaluate("""() => {
        const a = Array.from(document.querySelectorAll('a')).find(x => x.innerText.includes('條') && x.innerText.includes('次'));
        return a ? a.href : null;
    }""")
    print("條次 link:", link_tc)
    if link_tc:
        page.goto(link_tc, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        print("Page title:", page.title())
        content = page.content()
        print("Length:", len(content))
        print("Text preview:")
        print(page.locator("body").inner_text()[:400])
        links = page.evaluate("""() => Array.from(document.querySelectorAll('a')).map(x => ({text: x.innerText, href: x.href})).filter(x => x.text)""")
        print("Links count with text:", len(links))
        print("First 10 links:", links[:10])
    browser.close()

