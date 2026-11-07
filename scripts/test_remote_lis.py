import urllib.request
import sys

url = "https://lis.ly.gov.tw/lglawc/lglawkm"
req = urllib.request.Request(
    url,
    headers={"User-Agent": "LegalHubPersonal/1.0 (Windows NT 10.0; Win64; x64)"}
)
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        print("HTTP Status:", resp.status)
        content = resp.read().decode("utf-8", errors="replace")
        print("First 200 chars:")
        print(content[:200])
except Exception as e:
    print("Failed with error:", e)

