import urllib.request

url = "http://161.33.166.144/js/app.js"
try:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        content = resp.read().decode("utf-8")
        headers = dict(resp.headers)
        print("HTTP Status:", resp.status)
        print("Headers:", headers)
        print("Length:", len(content))
        has_minfa = "[\"civil_code\", \"民法\"]" in content
        has_zh_minfa = "[\"civil_code\", \"中華民國民法\"]" in content
        print("Contains [\"civil_code\", \"民法\"]:", has_minfa)
        print("Contains [\"civil_code\", \"中華民國民法\"]:", has_zh_minfa)
except Exception as e:
    print("Error:", e)

