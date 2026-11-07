"""
scripts/inspect_apa_lawsingle.py
"""
import os
import sys
import urllib.request
from bs4 import BeautifulSoup

url = "https://lis.ly.gov.tw/lglawc/lawsingle?0^1381C0620C81440381C0609781030399C8624E81130399E0620C"
req = urllib.request.Request(url, headers={"User-Agent": "LegalHubPersonal/1.0"})

sys.stdout.reconfigure(encoding='utf-8')

print("Fetching APA lawsingle page...")
with urllib.request.urlopen(req, timeout=15) as resp:
    html = resp.read().decode('utf-8', errors='replace')
    print("Status:", resp.status, "Length:", len(html))

with open("data/raw/lis/samples/apa_main_lawsingle.html", "w", encoding="utf-8") as f:
    f.write(html)

soup = BeautifulSoup(html, "html.parser")
print("Page Title:", soup.title.get_text() if soup.title else "")

print("\n--- Key text in apa_main_lawsingle ---")
for line in soup.get_text("\n", strip=True).splitlines()[:50]:
    if line.strip():
        print("  ", line)

print("\n--- All links in apa_main_lawsingle ---")
for a in soup.find_all("a"):
    txt = a.get_text(" ", strip=True)
    href = a.get("href", "")
    print(f"  [{txt}] -> {href}")

