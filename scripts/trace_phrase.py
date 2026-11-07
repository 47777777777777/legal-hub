import json
import glob

logs = glob.glob(r"C:\Users\harry\.gemini\antigravity\brain\ed7f1a6d-ba9f-401f-8aa8-4d33325c5647\.system_generated\logs\transcript_full.jsonl")
if not logs:
    logs = glob.glob(r"C:\Users\harry\.gemini\antigravity\brain\ed7f1a6d-ba9f-401f-8aa8-4d33325c5647\.system_generated\logs\transcript.jsonl")

for l in logs:
    with open(l, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if "最高行政法院九十九年" in line:
                obj = json.loads(line)
                step = obj.get("step_index")
                src = obj.get("source")
                typ = obj.get("type")
                c = obj.get("content") or ""
                t = obj.get("thinking") or ""
                print(f"Log {i}, Step {step}, Type {typ}, Source {src}")
                if "最高行政法院九十九年" in c:
                    pos = c.find("最高行政法院九十九年")
                    print(f"  Content snippet: {c[max(0, pos-40):min(len(c), pos+160)]}")
                if "最高行政法院九十九年" in t:
                    pos = t.find("最高行政法院九十九年")
                    print(f"  Thinking snippet: {t[max(0, pos-40):min(len(t), pos+160)]}")

