import json
import urllib.request
import ssl

with open('/home/ubuntu/legal-hub/data/ccu_session.json') as f:
    sess = json.load(f)

cookies = sess['cookies']
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

class CookieRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        print(f"Follow redirect {code} -> {newurl}")
        new_req = urllib.request.Request(newurl, headers=dict(req.headers))
        new_req.add_header('Cookie', cookies)
        return new_req

opener = urllib.request.build_opener(CookieRedirectHandler)

req = urllib.request.Request(
    'https://autorpa.lib.ccu.edu.tw/login/?url=https://www-lawbank-com-tw.autorpa.lib.ccu.edu.tw:8443/',
    headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Cookie': cookies,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
)

try:
    resp = opener.open(req)
    print("Final status:", resp.status, "URL:", resp.url)
    content = resp.read().decode('utf-8', errors='ignore')
    print("Title in HTML:", [l for l in content.splitlines() if '<title>' in l.lower()][:3])
    print("Contains lawbank:", "lawbank" in content.lower())
except Exception as e:
    print("Error:", e)
