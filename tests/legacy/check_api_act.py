import urllib.request
import json

url = "http://127.0.0.1:8080/api/acts/criminal_code"
with urllib.request.urlopen(url, timeout=5) as resp:
    data = json.loads(resp.read().decode("utf-8"))

articles = data["data"]["articles"]
titled = [a for a in articles if a.get("title")]
print(f"Total Criminal Code articles in act response: {len(articles)}")
print(f"Articles with titles in act response: {len(titled)}")
for a in titled[:8]:
    print(f"  第 {a['article_no']} 條：{a['title']}")

