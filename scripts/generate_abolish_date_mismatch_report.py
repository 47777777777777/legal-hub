import json
import re
import os
import sys
import csv

sys.stdout.reconfigure(encoding='utf-8')

CHLAW_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "ChLaw.json")
CHORDER_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "ChOrder.json")
OUT_CSV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports", "abolish_date_mismatch.csv")

CHN_DIGITS = {'〇': 0, '○': 0, 'O': 0, '零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}

def parse_num(s):
    if s.isdigit():
        return int(s)
    val, cur = 0, 0
    for char in s:
        if char in CHN_DIGITS:
            cur = CHN_DIGITS[char]
        elif char == '十':
            val += (cur if cur > 0 else 1) * 10
            cur = 0
        elif char == '百':
            val += (cur if cur > 0 else 1) * 100
            cur = 0
    return val + cur

def parse_date_from_text(text: str):
    m = re.search(r'中華民國\s*([〇○O零一二三四五六七八九十百0-9]+)\s*年\s*([〇○O零一二三四五六七八九十0-9]+)\s*月\s*([〇○O零一二三四五六七八九十0-9]+)\s*日', text)
    if not m:
        return None
    try:
        y = parse_num(m.group(1))
        mon = parse_num(m.group(2))
        d = parse_num(m.group(3))
        ad_y = y + 1911
        return f'{ad_y}{mon:02d}{d:02d}', f'民國 {y} 年 {mon:02d} 月 {d:02d} 日'
    except:
        return None

def split_history_items(hist: str):
    if not hist:
        return []
    raw_items = re.split(r'(?:^|\r?\n)\s*(?:[0-9]+[.\u3001]|\([0-9]+\))\s*', hist)
    items = [' '.join(x.split()) for x in raw_items if x.strip()]
    return items if items else [' '.join(hist.split())]

def main():
    with open(CHLAW_PATH, 'r', encoding='utf-8-sig') as f:
        laws = json.load(f)['Laws']
    with open(CHORDER_PATH, 'r', encoding='utf-8-sig') as f:
        orders = json.load(f)['Laws']

    all_acts = laws + orders
    abolished = [a for a in all_acts if a.get('LawAbandonNote') == '廢']

    mismatches = []
    matched_count = 0

    for a in abolished:
        pcode_m = re.search(r'[pP][cC]ode=([a-zA-Z0-9]+)', a.get('LawURL', ''))
        pcode = pcode_m.group(1).upper() if pcode_m else ''
        name = a.get('LawName', '')
        lmod = (a.get('LawModifiedDate') or '').strip()
        hist = a.get('LawHistories', '')
        items = split_history_items(hist)
        abolish_items = [it for it in items if '廢止' in it]

        if not abolish_items:
            last_text = items[-1] if items else ""
            mismatches.append({
                "pcode": pcode,
                "act_name": name,
                "law_modified_date": lmod,
                "parsed_history_date": "",
                "mismatch_reason": "沿革中無包含「廢止」之條目",
                "last_history_text": last_text
            })
            continue

        last_item = abolish_items[-1]
        parsed = parse_date_from_text(last_item)
        if not parsed:
            mismatches.append({
                "pcode": pcode,
                "act_name": name,
                "law_modified_date": lmod,
                "parsed_history_date": "",
                "mismatch_reason": "最後廢止沿革未解析出標準年月日",
                "last_history_text": last_item
            })
            continue

        hist_date_code, hist_date_str = parsed
        if hist_date_code != lmod:
            mismatches.append({
                "pcode": pcode,
                "act_name": name,
                "law_modified_date": lmod,
                "parsed_history_date": hist_date_code,
                "mismatch_reason": f"日期不一致 ({lmod} vs {hist_date_code})",
                "last_history_text": last_item
            })
        else:
            matched_count += 1

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with open(OUT_CSV, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            "pcode", "act_name", "law_modified_date", "parsed_history_date", "mismatch_reason", "last_history_text"
        ])
        writer.writeheader()
        writer.writerows(mismatches)

    print(f"Total Abolished: {len(abolished)}")
    print(f"Consistent: {matched_count}")
    print(f"Mismatches/Unmatchable: {len(mismatches)}")
    print(f"Report written to: {OUT_CSV}")

if __name__ == "__main__":
    main()
