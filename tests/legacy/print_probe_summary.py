import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

with open("data/raw/lawplayer/har/requests_summary.json", "r", encoding="utf-8") as f:
    d = json.load(f)

for target_id in ["civil_code_art_2", "cpc_art_244"]:
    info = d[target_id]
    print(f"=== Target: {target_id} ===")
    print(f"Title: {info['title']}")
    print(f"Total Requests: {info['requests_count']}")
    print(f"SVGs: {info['svg_count']}, Canvases: {info['canvas_count']}, Images: {len(info['images'])}")
    for tab_name, tab_data in info.get("tabs", {}).items():
        print(f"  Tab: {tab_name}")
        print(f"    Paywall detected: {tab_data.get('has_paywall')}")
        print(f"    Paywall banner: {tab_data.get('paywall_banner')}")
        print(f"    Reason text: {tab_data.get('reason_text')}")
        print(f"    Flowchart SVGs (>80x60): {len(tab_data.get('flowchart_svgs', []))}")

