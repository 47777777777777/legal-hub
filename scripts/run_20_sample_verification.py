import os
import sys
import time
import json
import re
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.lis.parser import parse_full_act_reasons, parse_lis_article_no

TARGET_ARTICLES = [
    "1", "2", "10", "25", "44", "45", "50", "68", "85", "92",
    "100", "110", "120", "127", "128", "131", "140", "160", "174-1", "175"
]

def clean_text(s):
    if not s:
        return ""
    # Normalize whitespace & strip
    return re.sub(r'\s+', ' ', s.replace('\xa0', ' ').replace('\u3000', ' ')).strip()

def parse_version_reason(html):
    soup = BeautifulSoup(html, 'html.parser')
    tables = soup.find_all('table')
    if not tables:
        return []
    target_table = tables[-1]
    articles = []
    cur_art = None
    for tr in target_table.find_all('tr'):
        txt = tr.get_text(separator=' ', strip=True)
        m_art = re.search(r'第([零一二三四五六七八九十百千萬\s]+(?:條\s*之\s*[零一二三四五六七八九十\s]+|條))\s*\((\w+)\)', txt)
        if m_art:
            if cur_art:
                articles.append(cur_art)
            art_raw = '第' + m_art.group(1).replace(' ', '')
            cur_art = {
                'article_no': parse_lis_article_no(art_raw),
                'article_no_raw': art_raw,
                'action_type': m_art.group(2),
                'content': '',
                'reason': ''
            }
            continue
        if cur_art:
            tds = [td.get_text(separator='\n', strip=True) for td in tr.find_all('td') if td.get_text(strip=True)]
            if len(tds) >= 2:
                if '條文' in tds[0]:
                    cur_art['content'] = tds[1]
                elif '理由' in tds[0]:
                    cur_art['reason'] = tds[1]

    if cur_art:
        articles.append(cur_art)
    return articles

def run_verification():
    print("=== Step 1: Parse Full Act Reasons from sample_1.html ===")
    s1_path = os.path.join(BASE_DIR, "data", "raw", "lis", "samples", "sample_1.html")
    with open(s1_path, "r", encoding="utf-8", errors="ignore") as f:
        full_html = f.read()
        
    full_act_records = parse_full_act_reasons(full_html)
    full_act_map = {}
    for r in full_act_records:
        no = r['article_no']
        if no not in full_act_map:
            full_act_map[no] = []
        full_act_map[no].append(r)
        
    print(f"Full Act parsed: {len(full_act_map)} distinct articles, {len(full_act_records)} total versions.")

    print("\n=== Step 2: Load Downloaded Raw Version Files ===")
    raw_ver_dir = os.path.join(BASE_DIR, "data", "raw", "lis", "versions")
    version_pages = {}
    for fname in os.listdir(raw_ver_dir):
        if fname.startswith("reason_") and fname.endswith(".html"):
            v_code = fname.replace("reason_", "").replace(".html", "")
            fpath = os.path.join(raw_ver_dir, fname)
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            version_pages[v_code] = {
                "file_path": fpath,
                "html": content,
                "parsed": parse_version_reason(content)
            }
            print(f"  Loaded {fname} ({v_code}): {len(content)} bytes, {len(version_pages[v_code]['parsed'])} articles")

    print("\n=== Step 3: Verbatim Character-by-Character Comparison ===")
    verification_results = []
    has_mismatch = False

    for target_no in TARGET_ARTICLES:
        if target_no not in full_act_map:
            print(f"ERROR: Target Art {target_no} not found in full act map!")
            has_mismatch = True
            continue
            
        full_versions = full_act_map[target_no]
        
        for f_ver in full_versions:
            v_date = f_ver['version_date']
            v_action = f_ver['action_type']
            f_reason = clean_text(f_ver.get('reason', ''))
            
            if v_date not in version_pages:
                print(f"Warning: Version {v_date} file not found!")
                has_mismatch = True
                continue
                
            single_parsed = version_pages[v_date]['parsed']
            s_match = next((x for x in single_parsed if x['article_no'] == target_no), None)
            
            if not s_match:
                print(f"MISMATCH: Art {target_no} ({v_date} {v_action}) not found in version reason page!")
                has_mismatch = True
                verification_results.append({
                    "article_no": target_no,
                    "version_date": v_date,
                    "action_type": v_action,
                    "status": "MISSING_IN_SINGLE",
                    "full_reason_preview": f_reason[:60],
                    "single_reason_preview": "NOT_FOUND",
                    "full_reason_len": len(f_reason),
                    "single_reason_len": 0,
                    "char_diff": -1
                })
                continue
                
            s_reason = clean_text(s_match.get('reason', ''))
            
            is_identical = (f_reason == s_reason)
            if not is_identical:
                has_mismatch = True
                print(f"MISMATCH on Art {target_no} ({v_date} {v_action}):")
                print(f"  Full Split len: {len(f_reason)}, Single len: {len(s_reason)}")
                print(f"  Full Split: {f_reason[:80]}")
                print(f"  Single    : {s_reason[:80]}")
                verification_results.append({
                    "article_no": target_no,
                    "version_date": v_date,
                    "action_type": v_action,
                    "status": "FAIL_MISMATCH",
                    "full_reason_len": len(f_reason),
                    "single_reason_len": len(s_reason),
                    "full_reason_preview": f_reason[:60],
                    "single_reason_preview": s_reason[:60],
                })
            else:
                verification_results.append({
                    "article_no": target_no,
                    "version_date": v_date,
                    "action_type": v_action,
                    "status": "PASS_IDENTICAL",
                    "full_reason_len": len(f_reason),
                    "single_reason_len": len(s_reason),
                    "full_reason_preview": f_reason[:60],
                    "single_reason_preview": s_reason[:60],
                })

    print(f"\nTotal comparison records: {len(verification_results)}")
    pass_cnt = sum(1 for r in verification_results if r['status'] == 'PASS_IDENTICAL')
    print(f"Pass count: {pass_cnt} / {len(verification_results)}")
    
    # Write report
    report_path = os.path.join(BASE_DIR, "reports", "lis_split_verification.md")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as rf:
        rf.write("# 行政程序法 20 條抽樣逐字比對驗證報告\n\n")
        rf.write(f"- 產生時間: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        rf.write(f"- 比對條數: 20 條 (涵蓋單版、多版、已刪除、第 128 條、第 174-1 條)\n")
        rf.write(f"- 比對版本總數: {len(verification_results)} 筆\n")
        rf.write(f"- 比對結果: {'全部逐字相符 (100% PASS)' if not has_mismatch else '有差異 (FAIL)'}\n\n")
        rf.write("## 比對明細清單\n\n")
        rf.write("| 條號 | 版本日期 | 動作 | 全法切分長度 | 單條/版頁長度 | 比對狀態 | 理由預覽 |\n")
        rf.write("|---|---|---|---|---|---|---|\n")
        for r in verification_results:
            rf.write(f"| 第 {r['article_no']} 條 | {r['version_date']} | {r['action_type']} | {r['full_reason_len']} 字 | {r['single_reason_len']} 字 | **{r['status']}** | {r['full_reason_preview']}... |\n")
            
        rf.write("\n## 結論與安全護欄\n\n")
        if not has_mismatch:
            rf.write("全法逐條立法理由（`sample_1.html`）切分出之所有版本立法理由，與立法院各次修法單版頁面逐字 100% 完全相符，字元零誤差，通過嚴格真實性驗證，准予執行全量入庫。\n")
        else:
            rf.write("比對發現字元差異，觸發安全護欄，已中斷入庫流程！\n")

    print(f"Report written to {report_path}")
    if has_mismatch:
        print("STOPPING! Mismatch found.")
        sys.exit(1)
    else:
        print("SUCCESS: 100% Pass!")

if __name__ == "__main__":
    run_verification()
