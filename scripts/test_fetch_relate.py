import sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

def main():
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
        print("URL2:", url2)
        page.goto(url2, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        
        # Check all relate links
        relate_links = page.evaluate("""() => {
            return Array.from(document.querySelectorAll('a'))
                .filter(x => x.querySelector('img[src*="relate"]'))
                .map(x => ({href: x.href, html: x.outerHTML}));
        }""")
        print(f"Total relate links on lawsingle: {len(relate_links)}")
        if relate_links:
            print("First 3 relate links:", relate_links[:3])
            
            # Navigate to 128
            link_128 = next((x['href'] for x in relate_links if '012800' in x['href']), None)
            print("Link 128:", link_128)
            if link_128:
                page.goto(link_128, wait_until="domcontentloaded")
                page.wait_for_timeout(1500)
                print("Page 128 URL:", page.url)
                print("Page 128 title:", page.title())
                c = page.content()
                print("Content length:", len(c))
                print("Has comptable:", "comptable" in c)
                print("Has 理由:", "理由" in c)
                
        browser.close()

if __name__ == "__main__":
    main()

