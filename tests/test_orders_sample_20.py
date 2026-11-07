import os
import sys
import json
import re
import urllib.request
import pytest
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE_PATH = os.path.join(BASE_DIR, "tests", "fixtures", "sample_20_orders.json")
CHORDER_PATH = os.path.join(BASE_DIR, "data", "ChOrder.json")

def test_orders_sample_20():
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        samples = json.load(f)
    
    with open(CHORDER_PATH, "r", encoding="utf-8-sig") as f:
        chorder = json.load(f)
    
    order_map = {}
    for l in chorder["Laws"]:
        m = re.search(r'[pP][cC]ode=([a-zA-Z0-9]+)', l.get("LawURL", ""))
        if m:
            order_map[m.group(1).lower()] = l

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        for item in samples:
            pcode = item["pcode"]
            expected_name = item["name"]
            expected_count = item["count"]
            raw_law = order_map.get(pcode)
            assert raw_law is not None, f"Order {pcode} not in ChOrder.json"

            # 1. Check API /api/acts/{pcode}
            api_url = f"http://127.0.0.1:8080/api/acts/{pcode}"
            req = urllib.request.urlopen(api_url)
            api_data = json.loads(req.read().decode("utf-8"))["data"]
            api_articles = api_data.get("articles", [])
            assert len(api_articles) == expected_count, (
                f"API count mismatch for {pcode}: expected {expected_count}, got {len(api_articles)}"
            )

            # 2. Check UI rendering
            page.goto(f"http://127.0.0.1:8080/#/act/{pcode}", wait_until="networkidle")
            page.wait_for_function(
                f"() => window.legalHubApp && window.legalHubApp.currentAct && "
                f"(window.legalHubApp.currentAct.pcode || '').toLowerCase() === '{pcode.lower()}' && "
                f"document.querySelectorAll('.stream-article-card').length === {expected_count}",
                timeout=10000
            )
            
            # Badge count
            badge_text = page.locator("#search-count-badge").text_content()
            assert f"{expected_count} 條" in badge_text, f"Badge mismatch: {badge_text} vs {expected_count}"

            # Rendered card count
            cards = page.locator(".stream-article-card")
            assert cards.count() == expected_count, (
                f"Card count mismatch for {pcode}: expected {expected_count}, got {cards.count()}"
            )

            # 3. Check 3 sample articles for verbatim fidelity and not_applicable LIS panel status
            sample_indices = [0, len(api_articles) // 2, len(api_articles) - 1]
            unique_indices = sorted(list(set(sample_indices)))
            
            for idx in unique_indices:
                art = api_articles[idx]
                art_no = art["article_no"]
                raw_art = next((a for a in raw_law["LawArticles"] if a.get("ArticleNo") in (art_no, f"第 {art_no} 條", f"{art_no}.")), None)
                if not raw_art:
                    continue
                
                expected_content = re.sub(r"\s+", "", raw_art["ArticleContent"])
                actual_content = re.sub(r"\s+", "", art["content"])
                assert expected_content == actual_content, f"Content mismatch in {pcode} art {art_no}"

                # Query Universal Article Panel API
                panel_url = f"http://127.0.0.1:8080/api/articles/{pcode}/{art_no}/panel"
                p_req = urllib.request.urlopen(panel_url)
                panel_data = json.loads(p_req.read().decode("utf-8"))["data"]

                assert panel_data["article"]["status"] == "present"
                assert panel_data["legislative_reasons"]["status"] == "not_applicable", (
                    f"Expected not_applicable for reasons in order {pcode}, got {panel_data['legislative_reasons']['status']}"
                )
                assert panel_data["amendment_comparison"]["status"] == "not_applicable", (
                    f"Expected not_applicable for comparison in order {pcode}, got {panel_data['amendment_comparison']['status']}"
                )

        browser.close()

