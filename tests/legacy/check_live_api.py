import urllib.request, json

url = "http://161.33.166.144/api/acts/civil_code"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode("utf-8"))
    act_data = data.get("data", {})
    name = act_data.get("name")
    arts = [(a["article_no"], a.get("title")) for a in act_data.get("articles", [])[:10]]
    with open(r"c:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub\scripts\live_api_res.txt", "w", encoding="utf-8") as f:
        f.write(f"Name: {name}\n")
        for num, title in arts:
            f.write(f"Art {num}: {title}\n")
print("CHECK COMPLETED")

