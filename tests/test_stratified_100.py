import os
import sys
import json
import time
import urllib.request
import re
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE_PATH = os.path.join(BASE_DIR, "tests", "fixtures", "stratified_100.json")

def test_stratified_100_articles():
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        samples = json.load(f)

    timings = {"path_a_list_click": [], "path_b_permalink": [], "path_c_dialer": []}
    status_distribution = {
        "article": {"present": 0, "source_has_none": 0, "not_attempted": 0, "not_applicable": 0},
        "legislative_reasons": {"present": 0, "source_has_none": 0, "not_attempted": 0, "not_applicable": 0},
        "amendment_comparison": {"present": 0, "source_has_none": 0, "not_attempted": 0, "not_applicable": 0},
        "lawplayer": {"present": 0, "source_has_none": 0, "not_attempted": 0, "not_applicable": 0}
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        
        js_errors = []
        page.on("pageerror", lambda e: js_errors.append(str(e)))

        for i, item in enumerate(samples):
            act_id = item["act_id"]
            art_no = str(item["article_no"])

            # 1. Fetch backend panel ground-truth
            panel_url = f"http://127.0.0.1:8080/api/articles/{act_id}/{art_no}/panel"
            with urllib.request.urlopen(panel_url) as resp:
                panel_data = json.loads(resp.read().decode("utf-8"))["data"]

            # Record status distribution
            for sec in ("article", "legislative_reasons", "amendment_comparison", "lawplayer"):
                st = panel_data.get(sec, {}).get("status", "not_attempted")
                status_distribution[sec][st] = status_distribution[sec].get(st, 0) + 1

            # Path B: Permalink Direct Access
            t0 = time.time()
            page.goto(f"http://127.0.0.1:8080/#/act/{act_id}/article/{art_no}", wait_until="networkidle")
            page.wait_for_function(
                f"() => window.legalHubApp && window.legalHubApp.currentAct && window.legalHubApp.currentAct.id === '{act_id}'",
                timeout=15000
            )
            page.wait_for_selector(f"#article-card-{art_no}", timeout=10000)
            page.wait_for_selector(f".drawer-hero-title:has-text('第 {art_no} 條')", timeout=10000)
            timings["path_b_permalink"].append(time.time() - t0)

            # Verbatim content check in drawer
            drawer_text = "".join(page.locator(".drawer-hero-article-box .para-body").all_text_contents())
            expected_content = re.sub(r"\s+", "", panel_data["article"]["content"])
            actual_content = re.sub(r"\s+", "", drawer_text)
            assert expected_content == actual_content, f"Content mismatch in {act_id} art {art_no}"

            # Path A: List Click (close drawer first, then click card to reopen)
            page.evaluate("() => { const d = document.getElementById('article-hover-popover'); if (d) d.classList.add('hidden'); const cb = document.getElementById('drawer-close-btn'); if (cb) cb.click(); }")
            t0 = time.time()
            page.evaluate(f"() => {{ window.legalHubApp.scrollToArticleCard('{art_no}'); const c = document.getElementById('article-card-{art_no}'); if (c) c.click(); }}")
            page.wait_for_selector(f".drawer-hero-title:has-text('第 {art_no} 條')", timeout=10000)
            timings["path_a_list_click"].append(time.time() - t0)

            # Path C: Dialer Jump (jump to article)
            t0 = time.time()
            page.evaluate(f"() => window.legalHubApp.loadAndJumpArticle('{art_no}')")
            page.wait_for_selector(f".drawer-hero-title:has-text('第 {art_no} 條')", timeout=10000)
            timings["path_c_dialer"].append(time.time() - t0)

            assert len(js_errors) == 0, f"JS error detected at sample {i} ({act_id} art {art_no}): {js_errors}"

        browser.close()

    # Calculate P50 / P95
    def calc_percentiles(arr):
        s = sorted(arr)
        p50 = s[int(len(s) * 0.50)]
        p95 = s[int(len(s) * 0.95)]
        return round(p50 * 1000, 1), round(p95 * 1000, 1)

    report_data = {
        "total_tested": len(samples),
        "status_distribution": status_distribution,
        "timings_ms": {
            k: {"p50_ms": calc_percentiles(v)[0], "p95_ms": calc_percentiles(v)[1]}
            for k, v in timings.items()
        }
    }

    report_path = os.path.join(BASE_DIR, "reports", "stratified_100_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)

    print("\n=== STRATIFIED 100 TEST REPORT ===")
    print(json.dumps(report_data, ensure_ascii=False, indent=2))
