import os
import sys
import time
import json
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HAR_DIR = os.path.join(BASE_DIR, "data", "raw", "lawplayer", "har")
os.makedirs(HAR_DIR, exist_ok=True)

TARGETS = [
    {
        "name": "civil_code_art_2",
        "label": "民法 第 2 條",
        "url": "https://lawplayer.com/article/6438cdc1e800e5f0b9327944"
    },
    {
        "name": "cpc_art_244",
        "label": "民事訴訟法 第 244 條",
        "url": "https://lawplayer.com/article/6438cf6fe800e5f0b9328b7a"
    }
]

def run_probe():
    print(f"=== Starting Real Browser Probe on LawPlayer (Slow Mo, Unauthenticated) ===")
    print(f"Output HAR directory: {HAR_DIR}")

    all_logs = {}

    with sync_playwright() as p:
        # Launch Chromium with realistic user agent
        browser = p.chromium.launch(headless=True)
        
        for target in TARGETS:
            tname = target["name"]
            turl = target["url"]
            print(f"\n---> Probing {target['label']}: {turl}")
            
            har_path = os.path.join(HAR_DIR, f"{tname}.har")
            context = browser.new_context(
                record_har_path=har_path,
                record_har_mode="minimal",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={"width": 1440, "height": 900}
            )
            page = context.new_page()
            
            requests_log = []
            
            def on_request(req):
                # Record XHR/Fetch/Document requests
                if req.resource_type in ["fetch", "xhr", "document", "script"]:
                    headers = req.headers
                    has_auth = "cookie" in headers or "authorization" in headers or "x-" in str(headers).lower()
                    requests_log.append({
                        "type": "request",
                        "url": req.url,
                        "method": req.method,
                        "resource_type": req.resource_type,
                        "headers": {k: v for k, v in headers.items() if k.lower() in ["cookie", "authorization", "accept", "content-type", "x-requested-with", "next-action"]},
                        "has_auth": has_auth,
                        "post_data": req.post_data[:500] if req.post_data else None
                    })
                    
            def on_response(resp):
                req = resp.request
                if req.resource_type in ["fetch", "xhr", "document"]:
                    body_preview = ""
                    try:
                        # Grab first 2KB of text body if possible
                        body = resp.body()
                        body_preview = body[:2048].decode("utf-8", errors="replace")
                    except Exception as e:
                        body_preview = f"<binary or decode error: {e}>"
                    
                    requests_log.append({
                        "type": "response",
                        "url": resp.url,
                        "status": resp.status,
                        "content_type": resp.headers.get("content-type", ""),
                        "body_preview_2kb": body_preview
                    })
            
            page.on("request", on_request)
            page.on("response", on_response)
            
            # Step 1: Navigate to page
            print(f"  Navigating to {turl}...")
            res = page.goto(turl, wait_until="networkidle", timeout=30000)
            print(f"  HTTP Response status: {res.status if res else 'None'}")
            time.sleep(2)
            
            # Step 2: Check for Cloudflare/Anti-bot
            body_html = page.content()
            if "Just a moment..." in body_html or "cf-mitigated" in body_html or (res and res.status == 403):
                print("  [ALERT] Cloudflare challenge / 403 detected! Halting probe.")
                context.close()
                return
                
            page_title = page.title()
            print(f"  Page title: {page_title}")
            
            # Take full initial screenshot
            init_shot = os.path.join(HAR_DIR, f"{tname}_page.png")
            page.screenshot(path=init_shot)
            print(f"  Saved initial screenshot: {init_shot}")
            
            # Step 3: Find interactive tabs / navigation buttons
            print("  Inspecting DOM for navigation tabs / anchors...")
            # Common LawPlayer tab buttons or anchors
            buttons_and_links = page.query_selector_all("button, nav a, [role='tab'], .tab-btn, a[href*='#']")
            print(f"  Found {len(buttons_and_links)} potential interactive elements.")
            
            # Click tabs with >= 1.5s interval
            tab_keywords = ["關鍵知識", "實務見解", "內容連結", "立法理由", "立法沿革", "沿革", "流程圖", "體系"]
            for kw in tab_keywords:
                try:
                    el = page.locator(f"text={kw}").first
                    if el.count() > 0 and el.is_visible():
                        print(f"  -> Found '{kw}' button/tab! Clicking...")
                        el.click()
                        time.sleep(2)
                        
                        # Take screenshot of clicked tab
                        tab_shot = os.path.join(HAR_DIR, f"{tname}_tab_{kw}.png")
                        page.screenshot(path=tab_shot)
                        print(f"     Saved tab screenshot: {tab_shot}")
                except Exception as e:
                    print(f"     Error clicking '{kw}': {e}")
                    
            # Step 4: Flowchart DOM Inspection
            print("  Inspecting DOM for Flowchart elements...")
            flow_info = {}
            # Look for flowchart anchors / containers
            flow_selectors = [
                "#w-flow", ".flowchart", "[class*='flow']", "[id*='flow']", 
                "svg.flowchart", ".flow-diagram", ".graph", "canvas", "svg"
            ]
            
            flow_found = False
            for sel in flow_selectors:
                elements = page.query_selector_all(sel)
                if elements:
                    for idx, el in enumerate(elements):
                        tag = el.evaluate("e => e.tagName.toLowerCase()")
                        cls = el.get_attribute("class") or ""
                        el_id = el.get_attribute("id") or ""
                        # Filter out small UI icons
                        box = el.bounding_box()
                        if box and box["width"] > 80 and box["height"] > 60:
                            flow_found = True
                            outer = el.evaluate("e => e.outerHTML")
                            flow_info[f"{sel}_{idx}"] = {
                                "tag": tag,
                                "id": el_id,
                                "class": cls,
                                "box": box,
                                "outer_snippet": outer[:1000]
                            }
                            # Save outerHTML snippet to file
                            with open(os.path.join(HAR_DIR, f"{tname}_flow_{sel}_{idx}.html"), "w", encoding="utf-8") as ff:
                                ff.write(outer)
                                
                            shot_path = os.path.join(HAR_DIR, f"{tname}_flow_{sel}_{idx}.png")
                            el.screenshot(path=shot_path)
                            print(f"     Captured Flowchart DOM ({tag}#{el_id}.{cls}): {box['width']}x{box['height']} -> {shot_path}")
                            
            if not flow_found:
                print("  No visible flowchart canvas/svg (>80x60) found on page.")
                
            # Step 5: Legislative Reasons DOM Inspection
            print("  Inspecting DOM for Legislative Reasons...")
            reasons_selectors = [
                "#w-reason", "#w-history", "[class*='reason']", "[class*='history']", 
                "[class*='amend']", ".artw-history", ".artw-reason"
            ]
            reasons_found = {}
            for sel in reasons_selectors:
                els = page.query_selector_all(sel)
                for idx, el in enumerate(els):
                    txt = el.inner_text().strip()
                    if txt:
                        reasons_found[f"{sel}_{idx}"] = txt[:1000]
                        print(f"     Found Legislative Reason text under '{sel}': {txt[:120]}...")
                        
            # Save target log summary
            all_logs[tname] = {
                "target": target,
                "title": page_title,
                "requests_count": len(requests_log),
                "requests": requests_log,
                "flowchart_dom": flow_info,
                "reasons_dom": reasons_found
            }
            
            context.close()
            print(f"  Closed context. HAR written to {har_path}")
            time.sleep(1.5)

        browser.close()

    # Save complete requests summary
    summary_path = os.path.join(HAR_DIR, "requests_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(all_logs, f, ensure_ascii=False, indent=2)
    print(f"\n=== Probe Complete. Summary saved to {summary_path} ===")

if __name__ == "__main__":
    run_probe()

