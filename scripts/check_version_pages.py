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
    
    # Get all version links
    ver_links = page.evaluate("""() => {
        return Array.from(document.querySelectorAll('a'))
            .filter(x => x.innerText.includes('中華民國'))
            .map(x => ({text: x.innerText, href: x.href}));
    }""")
    print("Found version links:", len(ver_links))
    for v in ver_links:
        print(" ", v['text'], "->", v['href'])
        
    # Check 104年12月11日
    v_104 = next((x['href'] for x in ver_links if '104' in x['text']), None)
    if v_104:
        page.goto(v_104, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        btn1_104 = page.evaluate("""() => {
            const a = document.querySelector('a img[src*="yellow_btn01"]');
            return a ? a.parentElement.href : null;
        }""")
        print("104 btn1:", btn1_104)
        if btn1_104:
            page.goto(btn1_104, wait_until="domcontentloaded")
            page.wait_for_timeout(1500)
            print("104 Reason page preview:")
            print(page.locator("body").inner_text()[:400])
            
    browser.close()

