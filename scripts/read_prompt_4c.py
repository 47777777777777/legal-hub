import json

transcript_path = r"C:\Users\harry\.gemini\antigravity\brain\ed7f1a6d-ba9f-401f-8aa8-4d33325c5647\.system_generated\logs\transcript_full.jsonl"
with open(transcript_path, 'r', encoding='utf-8') as f:
    for line in f:
        if 'Prompt 4C' in line:
            obj = json.loads(line)
            if obj.get('type') == 'USER_INPUT':
                print("FOUND STEP:", obj.get('step_index'))
                with open("docs/prompt_4c_full.md", "w", encoding="utf-8") as out:
                    out.write(obj.get('content', ''))
                print("Written to docs/prompt_4c_full.md, length:", len(obj.get('content', '')))
                break

