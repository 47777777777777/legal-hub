"""
scripts/fetch_lis_samples_direct.py

Directly fetches the 3 LIS sample URLs and lglawkm entry portal using urllib with
User-Agent: LegalHubPersonal/1.0.
Saves raw HTML and response headers.
"""

import os
import sys
import time
import json
import urllib.request
import urllib.error

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


def fetch_and_save():
    print("=== Fetching LIS Samples with LegalHubPersonal/1.0 ===")
    for name, url in URLS:
        print(f"\nFetching {name}: {url} ...")
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                status = resp.status
                headers = dict(resp.headers)
                body = resp.read()
                print(f"Status: {status}, Content-Length: {len(body)}")

                html_path = os.path.join(SAMPLES_DIR, f"{name}.html")
                with open(html_path, "wb") as f:
                    f.write(body)

                headers_path = os.path.join(SAMPLES_DIR, f"{name}.headers.json")
                with open(headers_path, "w", encoding="utf-8") as f:
                    json.dump({"status": status, "headers": headers, "url": url}, f, ensure_ascii=False, indent=2)

                print(f"Saved: {html_path}")
        except Exception as e:
            print(f"Failed to fetch {name}: {e}")

        # Rate limiting: >= 1s between requests
        time.sleep(1.2)


if __name__ == "__main__":
    fetch_and_save()

