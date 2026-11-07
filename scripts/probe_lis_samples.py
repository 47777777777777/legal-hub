"""
scripts/probe_lis_samples.py

Uses Playwright to fetch the 3 LIS sample URLs and lglawkm entry portal.
Saves raw HTML and inspects page DOM structure.
"""

import os
import sys
import time
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES_DIR = os.path.join(BASE_DIR, "data", "raw", "lis", "samples")
os.makedirs(SAMPLES_DIR, exist_ok=True)

URLS = [
    ("sample_1", "https://lis.ly.gov.tw/lglawc/lawsingle?001D18E6E7520000000000000000032000000007000000^01830109123000^00000000000"),
    ("sample_2", "https://lis.ly.gov.tw/lglawc/lawsingle?001D18E6E752000000000000000005A00000000C00FFFFFD00^01830109123000^00000000000"),
    ("sample_3", "https://lis.ly.gov.tw/lglawc/lawsingle?001D18E6E7520000000000000000014000000004000000^01830109123000^00000000000"),
    ("lglawkm_entry", "https://lis.ly.gov.tw/lglawc/lglawkm")
]

USER_AGENT = "LegalHubPersonal/1.0"


def main():
    print("=== Probing LIS (lis.ly.gov.tw) Sample Pages ===")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1280, "height": 900}
        )
        page = context.new_page()

        for name, url in URLS:
            print(f"\n--- Loading {name}: {url} ---")
            try:
                resp = page.goto(url, wait_until="networkidle", timeout=30000)
                status = resp.status if resp else 0
                print(f"Status: {status}")
                page_title = page.title()
                print(f"Page Title: {page_title}")

                html = page.content()
                save_path = os.path.join(SAMPLES_DIR, f"{name}.html")
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(html)
                print(f"Saved raw HTML ({len(html)} bytes) to: {save_path}")

                # Take screenshot
                ss_path = os.path.join(SAMPLES_DIR, f"{name}.png")
                page.screenshot(path=ss_path, full_page=True)
                print(f"Saved screenshot to: {ss_path}")

            except Exception as e:
                print(f"Error loading {url}: {e}")

            time.sleep(1.5)

        browser.close()
    print("\nProbing completed.")


if __name__ == "__main__":
    main()

