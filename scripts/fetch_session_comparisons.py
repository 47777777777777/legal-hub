from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import os

OUT_DIR = "data/raw/lis/comparisons"
os.makedirs(OUT_DIR, exist_ok=True)

# The amendment dates for APA:
# Note: 0880115 is enactment (制定), which has no comparison table.
# The remaining 7 amendment dates are:
dates = ['0891208', '0900605', '0901228', '0941206', '1020430', '1041211', '1091230']

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(user_agent="LegalHubPersonal/1.0")
    
    # Establish session
    page.goto("https://lis.ly.gov.tw/lglawc/lglawkm", wait_until="domcontentloaded")
    page.fill("input[name='_1_6_T']", "行政程序法")
    page.click("input[name='_IMG_檢索']")
    page.wait_for_timeout(1500)
    
    # Get law link
    law_url = page.evaluate("""() => {
        const a = Array.from(document.querySelectorAll('a')).find(x => x.innerText.trim() === '行政程序法' && x.href.includes('lawsingle'));
        return a ? a.href : null;
    }""")
    print("Law link:", law_url)
    
    # Extract session prefix (e.g. 00EC430A9E77...)
    # The URL looks like https://lis.ly.gov.tw/lglawc/lawsingle?00XXXXXX...^01830...
    page.goto(law_url, wait_until="domcontentloaded")
    page.wait_for_timeout(1500)
    
    curr_url = page.url
    print("Current URL:", curr_url)
    # The session key is the part between ? and ^ or first 12 chars
    query = curr_url.split("?")[1] if "?" in curr_url else ""
    session_id = query[:12] if len(query) >= 12 else ""
    print("Session ID:", session_id)
    
    for d in dates:
        # Comparison table URL pattern
        comp_url = f"https://lis.ly.gov.tw/lglawc/lawsingle?{session_id}000000000000000005A00000000C00FFFFFD00^01830{d}00^00000000000"
        page.goto(comp_url, wait_until="domcontentloaded")
        page.wait_for_timeout(1000)
        
        content = page.content()
        soup = BeautifulSoup(content, 'html.parser')
        tbls = soup.find_all('table')
        has_comp = any('版本條文' in t.get_text() for t in tbls)
        out_path = os.path.join(OUT_DIR, f"comp_{d}.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Date {d}: URL={comp_url} -> len={len(content)}, has_comp={has_comp}")
        
    browser.close()

