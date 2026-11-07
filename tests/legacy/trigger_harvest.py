import urllib.request, json, time, sys

sys.stdout.reconfigure(encoding='utf-8')

req = urllib.request.Request(
    "http://161.33.166.144/api/ccu/harvest/start",
    data=json.dumps({"act_id": "criminal_code", "reset": True}).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)
with urllib.request.urlopen(req, timeout=5) as resp:
    print("Start harvest response:", resp.read().decode("utf-8"))

time.sleep(3)

# Check harvest status
with urllib.request.urlopen("http://161.33.166.144/api/ccu/harvest/status", timeout=5) as resp:
    res = json.loads(resp.read().decode("utf-8"))
    status = res.get("data", {})
    print("Is running:", status.get("is_running"))
    print("Current action:", status.get("current_action"), "| percent:", status.get("percent"))
    print("Total harvested:", status.get("total_harvested"))
    print("Skipped duplicates:", status.get("total_skipped_duplicates"))
    print("Recent logs:")
    for l in status.get("logs", [])[-8:]:
        print(" ", l)
