import urllib.request
import re

req = urllib.request.Request(
    'https://lis.ly.gov.tw/lglawc/lglawkm',
    headers={'User-Agent': 'Mozilla/5.0'}
)
with urllib.request.urlopen(req) as resp:
    raw = resp.read()

print('Meta charset:', re.findall(b'charset=[^"\' >]*', raw, re.I))
print("big5 contains 立法院:", '立法院' in raw.decode('big5', errors='ignore'))
print("utf-8 contains 立法院:", '立法院' in raw.decode('utf-8', errors='ignore'))
