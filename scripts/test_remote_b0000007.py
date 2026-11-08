import urllib.request
import json

url = "http://161.33.166.144/api/acts/b0000007"
req = urllib.request.urlopen(url, timeout=10)
data = json.loads(req.read().decode("utf-8"))
act = data.get("data", {})
articles = act.get("articles", [])
reasons_count = sum(len(a.get("lis_reasons", [])) for a in articles)
versions_count = sum(len(a.get("lis_versions", [])) for a in articles)

print("Remote API Status:", data.get("success"))
print("Act Name:", act.get("name"))
print("Total Articles:", len(articles))
print("Total LIS Reasons across articles:", reasons_count)
print("Total LIS Version Cards across articles:", versions_count)
first_reason = next((a for a in articles if a.get("lis_reasons")), None)
if first_reason:
    print(f"Sample Art {first_reason['article_no']} Status:", first_reason.get("lis_reasons_status"))
    print(f"Sample Art {first_reason['article_no']} Reasons count:", len(first_reason.get("lis_reasons", [])))
