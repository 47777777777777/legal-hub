import sys
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

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
    
    page.goto(btn1, wait_until="domcontentloaded")
    page.wait_for_timeout(1500)
    
    soup = BeautifulSoup(page.content(), "html.parser")
    print("Forms on btn1 page:", len(soup.find_all("form")))
    for f in soup.find_all("form"):
        print("Form attrs:", f.attrs)
        for inp in f.find_all(["input", "select"]):
            print(" ", inp.name, inp.get("type"), inp.get("value"), [o.text for o in inp.find_all("option")][:5] if inp.name=="select" else "")
            
    print("Links on btn1 page:")
    for a in soup.find_all("a"):
        print(" ", a.get_text(strip=True), a.get("href"))
        
    browser.close()

