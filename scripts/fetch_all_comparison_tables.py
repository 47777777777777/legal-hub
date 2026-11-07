import os
import json
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

OUT_DIR = "data/raw/lis/comparisons"
os.makedirs(OUT_DIR, exist_ok=True)

def fetch_comparisons(law_name="行政程序法"):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent="LegalHubPersonal/1.0")
        
        # Step 1: Search portal
        page.goto("https://lis.ly.gov.tw/lglawc/lglawkm", wait_until="domcontentloaded")
        page.fill("input[name='_1_6_T']", law_name)
        page.click("input[name='_IMG_檢索']")
        page.wait_for_timeout(1500)
        
        # Step 2: Act entry link
        url2 = page.evaluate(f"""() => {{
            const a = Array.from(document.querySelectorAll('a')).find(x => x.innerText.trim() === '{law_name}' && x.href.includes('lawsingle'));
            return a ? a.href : null;
        }}""")
        print(f"Step 2: Law link -> {url2}")
        if not url2:
            print("Failed to find law link.")
            browser.close()
            return
            
        page.goto(url2, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        
        # In main act page, find all amendment links
        amend_links = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('a').forEach(a => {
                const txt = a.innerText.trim();
                if ((txt.includes('制定') || txt.includes('修正')) && a.href.includes('lawsingle')) {
                    results.push({ text: txt, href: a.href });
                }
            });
            return results;
        }""")
        print(f"Found {len(amend_links)} amendment links:")
        for al in amend_links:
            print(f"  {al['text']} -> {al['href']}")
            
        # For each amendment link, visit and check for "修正條文對照表" or comparison buttons
        for al in amend_links:
            txt = al['text']
            page.goto(al['href'], wait_until="domcontentloaded")
            page.wait_for_timeout(1000)
            
            # Check for comparison table button / link
            comp_link = page.evaluate("""() => {
                const a = Array.from(document.querySelectorAll('a, input, button')).find(x => {
                    const t = (x.innerText || x.value || '').trim();
                    return t.includes('對照表') || t.includes('修正條文對照');
                });
                if (a) {
                    return a.href || a.getAttribute('onclick') || a.name || 'found';
                }
                return null;
            }""")
            print(f"\nAmendment: {txt}")
            print(f"  Comparison element: {comp_link}")
            
            # Also check if current page already has comparison table or if clicking button loads it
            # In LIS, button code 05A00000000C00 is for comparison table.
            # Let's inspect all buttons/links on this amendment page:
            btn_info = page.evaluate("""() => {
                return Array.from(document.querySelectorAll('a, input[type=\"button\"], input[type=\"image\"]')).map(x => ({
                    tag: x.tagName,
                    text: (x.innerText || x.value || x.alt || '').trim(),
                    href: x.href || null,
                    onclick: x.getAttribute('onclick') || null,
                    name: x.name || null
                })).filter(x => x.text || x.name);
            }""")
            for b in btn_info:
                if any(k in (b['text'] or '') for k in ['對照', '理由', '條文', '沿革', '異動']):
                    print(f"    Btn: {b['tag']} | text='{b['text']}' | href={b['href']} | onclick={b['onclick']}")
                    
            # If there is a comparison table link/button, click it or navigate to it
            has_comp = False
            for b in btn_info:
                if '對照' in (b['text'] or ''):
                    if b['href']:
                        page.goto(b['href'], wait_until="domcontentloaded")
                    elif b['onclick']:
                        # Execute onclick or click element
                        page.click(f"input[value*='對照'], a:has-text('對照')")
                    page.wait_for_timeout(1500)
                    has_comp = True
                    break
                    
            if has_comp:
                content = page.content()
                print(f"  -> Got comparison page: len={len(content)}")
                # save raw
                safe_name = "".join(c for c in txt if c.isalnum() or c in ('_', '-'))
                out_path = os.path.join(OUT_DIR, f"{safe_name}.html")
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"  -> Saved to {out_path}")
                
        browser.close()

if __name__ == "__main__":
    fetch_comparisons()

