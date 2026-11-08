import socket
import time
import sys
import os

# Monkeypatch socket.getaddrinfo to force IPv4
orig_getaddrinfo = socket.getaddrinfo
def getaddrinfo_ipv4(host, port, family=0, type=0, proto=0, flags=0):
    return orig_getaddrinfo(host, port, family=socket.AF_INET, type=type, proto=proto, flags=flags)
socket.getaddrinfo = getaddrinfo_ipv4

BASE_DIR = r"C:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub"
sys.path.insert(0, BASE_DIR)

from scripts.lis_crawler_pipeline import LisCrawler

crawler = LisCrawler()

law_name = "國家運動科學中心設置條例"
act_id = "h0000185"
pcode = "H0000185"

print(f"=== Testing IPv4 Forced Crawl on {law_name} ===")

t0 = time.time()
res = crawler.crawl_act(law_name, act_id, pcode)
t1 = time.time()

print(f"Success: {res.get('success')}, Reasons: {res.get('reasons_count')}, Req count: {res.get('req_count')}")
print(f"Total time taken with IPv4 forced: {round(t1 - t0, 2)}s (was 85.95s!)")

