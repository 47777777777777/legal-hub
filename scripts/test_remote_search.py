import urllib.request, urllib.parse, json

q = urllib.parse.quote("論刑法總則規範在2015年度司法實務之演進")
url = f"http://161.33.166.144/api/ccu/search?q={q}"
try:
    with urllib.request.urlopen(url, timeout=5) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        print("Success:", data.get("success"))
        print("Total found:", len(data.get("data", [])))
        for it in data.get("data", []):
            print("Found:", it.get("title"), "| Source:", it.get("source"), "| is_local:", it.get("is_local"))
except Exception as e:
    print("Error:", e)

