from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import os
import re

OUT_DIR = "data/raw/lis/comparisons"
os.makedirs(OUT_DIR, exist_ok=True)

# 7 amendment dates for Administrative Procedure Act (01830)
DATES = ['0891208', '0900605', '0901228', '0941206', '1020430', '1041211', '1091230']

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent="LegalHubPersonal/1.0")
        
        # 1. Search portal
        page.goto("https://lis.ly.gov.tw/lglawc/lglawkm", wait_until="domcontentloaded")
        page.fill("input[name='_1_6_T']", "行政程序法")
        page.click("input[name='_IMG_檢索']")
        page.wait_for_timeout(1500)
        
        # 2. Main entry link
        law_url = page.evaluate("""() => {
            const a = Array.from(document.querySelectorAll('a')).find(x => x.innerText.trim() === '行政程序法' && x.href.includes('lawsingle'));
            return a ? a.href : null;
        }""")
        print("Law URL:", law_url)
        page.goto(law_url, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        
        content = page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Find all links on the act page
        all_links = [a.get('href') for a in soup.find_all('a') if a.get('href')]
        lawsingle_links = [h for h in all_links if 'lawsingle?' in h]
        print(f"Total lawsingle links: {len(lawsingle_links)}")
        for l in lawsingle_links[:10]:
            print("  ", l)
            
        # Find session token from a link matching lawsingle?[0-9A-F]{12}
        session_token = None
        tail = "00000000000"
        for l in lawsingle_links:
            m = re.search(r'lawsingle\?([0-9A-Fa-f]{12}).*\^([0-9A-Za-z]+)$', l)
            if m:
                session_token = m.group(1)
                tail = m.group(2)
                break
                
        print("Extracted Session Token:", session_token, "Tail:", tail)
        if not session_token:
            print("Could not find 12-char session token, checking query params:")
            for l in lawsingle_links:
                print("  param:", l.split('lawsingle?')[1] if 'lawsingle?' in l else '')
            browser.close()
            return
            
        for d in DATES:
            comp_url = f"https://lis.ly.gov.tw/lglawc/lawsingle?{session_token}000000000000000005A00000000C00FFFFFD00^01830{d}00^{tail}"
            print(f"\nNavigating to Date {d}: {comp_url}")
            page.goto(comp_url, wait_until="domcontentloaded")
            page.wait_for_timeout(1500)
            
            c = page.content()
            has_comp = '版本條文' in c or 'comptable' in c
            out_file = os.path.join(OUT_DIR, f"comp_{d}.html")
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(c)
            print(f"  -> len={len(c)}, has_comp={has_comp}, saved to {out_file}")
            
        browser.close()

if __name__ == "__main__":
    main()
