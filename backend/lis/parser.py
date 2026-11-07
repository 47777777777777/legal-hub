"""
立法院法律系統 (lis.ly.gov.tw/lglawc) 專用解析器
純函式設計：輸入原始 HTML 字串，輸出結構化字典，不包含任何猜測、AI 生成或手寫假資料。
"""
import re
import json
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup


CN_DIGITS = {'零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}
CN_UNITS = {'十': 10, '百': 100, '千': 1000, '萬': 10000}


def cn_to_int(cn: str) -> int:
    """將中文大寫數字轉換為整數 (例如 第一百二十八 -> 128)"""
    if not cn:
        return 0
    # 若全是純數字字元
    if all(c in CN_DIGITS for c in cn):
        return int(''.join(str(CN_DIGITS[c]) for c in cn))

    val = 0
    curr = 0
    for char in cn:
        if char in CN_DIGITS:
            curr = CN_DIGITS[char]
        elif char in CN_UNITS:
            unit = CN_UNITS[char]
            if curr == 0:
                curr = 1  # 例如 "十" 開頭代表 10
            val += curr * unit
            curr = 0
    val += curr
    return val


def parse_lis_article_no(raw_str: str) -> str:
    """
    將立法院的中文條號字串正規化為標準條號 (MOJ 格式)
    例: '第一條' -> '1'
        '第一百二十八條' -> '128'
        '第一百七十四條之一' -> '174-1'
        '第一百七十四條 之一' -> '174-1'
    """
    s = raw_str.replace('第', '').replace(' ', '').strip()
    if '條' in s:
        parts = s.split('條')
        main_part = parts[0].strip()
        sub_part = ''.join(parts[1:]).replace('之', '').strip()
        main_no = cn_to_int(main_part)
        if sub_part:
            sub_no = cn_to_int(sub_part)
            return f"{main_no}-{sub_no}"
        return str(main_no)
    return str(cn_to_int(s))


def parse_full_act_reasons(
    html_content: str,
    raw_path: str = "",
    source_url: str = ""
) -> List[Dict[str, Any]]:
    """
    解析全法全文含立法理由頁 (對應 sample_1.html)
    回傳每條條文及其逐字立法理由列表。
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    results = []

    # 取得最底層的條文表格 (無嵌套子 table 的 leaf table)
    leaf_tables = [t for t in soup.find_all('table') if len(t.find_all('table')) == 0]

    for tbl in leaf_tables:
        raw_text = tbl.get_text(separator='\n', strip=True)
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        if not lines:
            continue

        # 檢查是否為條文表格 (第一列或前幾列包含條號)
        header_line = None
        for l in lines[:4]:
            if re.search(r'第[零一二三四五六七八九十百千萬\s]+條', l):
                header_line = l
                break

        if not header_line:
            continue

        # 條號
        m_art = re.search(r'(第[零一二三四五六七八九十百千萬\s]+(?:條之[零一二三四五六七八九十\s]+|條\s*之\s*[零一二三四五六七八九十\s]+|條))', raw_text)
        if not m_art:
            continue
        art_raw = m_art.group(1).replace(' ', '')
        art_no = parse_lis_article_no(art_raw)

        # 逐版本解析：條文與理由可能有多個歷史版本 (例如 (0880115 制定) 及 (1091230 修正))
        versions = []
        cur_v = None
        target = None

        for line in lines:
            m_paren = re.search(r'^\(([0-9]{7})\s*([^\)]+)\)$', line)
            if m_paren:
                if cur_v:
                    versions.append(cur_v)
                cur_v = {
                    "version_date": m_paren.group(1),
                    "action_type": m_paren.group(2).strip(),
                    "date_label_raw": line.strip(),
                    "date_raw": m_paren.group(1),
                    "content_lines": [],
                    "reason_lines": []
                }
                target = None
                continue
            elif line == '條文':
                target = 'content'
                continue
            elif line == '理由':
                target = 'reason'
                continue
            elif line.startswith('第') and '條' in line:
                continue
            elif '立法院國會圖書館' in line or 'Copyright' in line:
                break

            if cur_v and target == 'content':
                cur_v["content_lines"].append(line)
            elif cur_v and target == 'reason':
                cur_v["reason_lines"].append(line)

        if cur_v:
            versions.append(cur_v)

        for v in versions:
            c = '\n'.join(v["content_lines"]).strip()
            r = '\n'.join(v["reason_lines"]).strip()
            if art_no and (c or r):
                results.append({
                    "article_no": art_no,
                    "article_no_raw": art_raw,
                    "version_date": v["version_date"],
                    "action_type": v["action_type"],
                    "date_label_raw": v.get("date_label_raw", f"({v['version_date']} {v['action_type']})"),
                    "date_raw": v.get("date_raw", v["version_date"]),
                    "article_no_at_the_time": art_raw,
                    "source_mode": "fullpage",
                    "content": c,
                    "reason": r,
                    "source": "立法院法律系統",
                    "source_url": source_url,
                    "raw_path": raw_path
                })

    return results


def parse_comparisons_from_html(
    html_content: str,
    raw_path: str = "",
    source_url: str = ""
) -> List[Dict[str, Any]]:
    """
    解析新舊修正條文對照表頁面，支援單頁包含單一或多條修正條文。
    保留原始表頭與結構化儲存格陣列。
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    comptbl = soup.find('div', id='comptable')
    if not comptbl:
        for tbl in soup.find_all('table'):
            txt = tbl.get_text(separator=' ', strip=True)
            if '版本法名稱' in txt and '版本條文' in txt:
                comptbl = tbl
                break
    if not comptbl:
        return []
        
    main_tbl = comptbl.find('table') if comptbl.name != 'table' else comptbl
    if not main_tbl:
        return []
        
    rows = []
    for tr in main_tbl.find_all('tr'):
        cells = [td.get_text(separator='\n', strip=True) for td in tr.find_all(['td', 'th'])]
        if cells and not (len(cells) == 1 and 'Copyright' in cells[0]):
            rows.append(cells)
            
    if len(rows) < 3:
        return []
        
    law_name = ""
    new_version_date = ""
    old_version_date = ""
    col_headers = []
    
    for r in rows:
        if len(r) >= 2 and r[0] == '版本法名稱':
            law_name = r[1].strip()
        elif len(r) >= 2 and r[0] == '版本條文':
            new_version_date = r[1].strip()
            if len(r) >= 3:
                old_version_date = r[2].strip()
            col_headers = r
            
    entries = []
    curr_art = None
    for r in rows:
        if not r:
            continue
        label = r[0]
        if '條' in label and any(k in label for k in ['修正', '增訂', '刪除']):
            m = re.search(r'(第[零一二三四五六七八九十百千萬\s]+(?:條之[零一二三四五六七八九十\s]+|條))\s*(?:\(([^\)]+)\))?', label)
            art_raw = m.group(1).replace(' ', '').strip() if m else label.strip()
            action_type = m.group(2) if m else ''
            curr_art = {
                'art_raw': art_raw,
                'action_type': action_type,
                'new_content': r[1].strip() if len(r) > 1 else '',
                'old_content': r[2].strip() if len(r) > 2 else '',
                'art_row': r,
                'reason': '',
                'reason_row': []
            }
            entries.append(curr_art)
        elif label == '理由' and curr_art:
            curr_art['reason'] = r[1].strip() if len(r) > 1 else ''
            curr_art['reason_row'] = r
            
    results = []
    for e in entries:
        art_no = parse_lis_article_no(e['art_raw'])
        specific_rows = [
            ['版本法名稱', law_name] + ([law_name] if old_version_date else []),
            col_headers,
            e['art_row']
        ]
        if e['reason_row']:
            specific_rows.append(e['reason_row'])
        results.append({
            'law_name': law_name,
            'article_no': art_no,
            'article_no_raw': e['art_raw'],
            'action_type': e['action_type'],
            'new_version_date': new_version_date,
            'old_version_date': old_version_date,
            'new_content': e['new_content'],
            'old_content': e['old_content'],
            'reason': e['reason'],
            'table_rows': specific_rows,
            'col_headers_json': json.dumps(col_headers, ensure_ascii=False),
            'cells_json': json.dumps(specific_rows, ensure_ascii=False),
            'date_label_raw': f"({new_version_date} {e['action_type']})" if (new_version_date or e['action_type']) else '',
            'date_raw': new_version_date,
            'article_no_at_the_time': e['art_raw'],
            'source_mode': 'singlepage',
            'source': '立法院法律系統',
            'source_url': source_url,
            'raw_path': raw_path
        })
    return results


def parse_comparison_table(
    html_content: str,
    raw_path: str = "",
    source_url: str = ""
) -> Dict[str, Any]:
    """
    解析新舊修正條文對照表頁面 (相容回傳單條或第一條)
    """
    res = parse_comparisons_from_html(html_content, raw_path, source_url)
    return res[0] if res else {}


def parse_single_article(
    html_content: str,
    raw_path: str = "",
    source_url: str = ""
) -> Dict[str, Any]:
    """
    解析立法院單一條文頁面 (對應 sample_3.html)
    提取條文原文、理由與對照表超連結。
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    comparison_url = ""
    for a in soup.find_all('a'):
        img = a.find('img')
        if img and 'yellow_btn05' in img.get('src', ''):
            comparison_url = a.get('href', '')
            break

    full_text = soup.get_text(separator='\n', strip=True)
    lines = [l.strip() for l in full_text.splitlines() if l.strip()]

    law_name = ""
    law_code = ""
    v_date_str = ""
    art_raw = ""
    action_type = ""
    content_lines = []
    reason_lines = []
    target = None

    for idx, line in enumerate(lines):
        if line == '立法院法律系統':
            continue
        elif not law_name and '法' in line:
            law_name = line
            continue
        elif line.startswith('(') and line.endswith(')') and line[1:-1].isdigit():
            law_code = line[1:-1]
            continue
        elif any(k in line for k in ['年', '月', '日']) and not v_date_str and ('一' in line or '二' in line or '八' in line or '九' in line or '十' in line):
            v_date_str = line
            continue
        elif re.search(r'^第[零一二三四五六七八九十百千萬\s]+條', line):
            art_raw = line.replace(' ', '')
            continue
        elif line.startswith('(') and any(k in line for k in ['修正', '制定', '增訂', '刪除']) and line.endswith(')'):
            action_type = line[1:-1]
            continue
        elif line == '條文':
            target = 'content'
            continue
        elif line == '理由':
            target = 'reason'
            continue
        elif '立法院國會圖書館' in line or 'Copyright' in line:
            break

        if target == 'content':
            content_lines.append(line)
        elif target == 'reason':
            reason_lines.append(line)

    art_no = parse_lis_article_no(art_raw) if art_raw else ""

    return {
        "law_name": law_name,
        "law_code": law_code,
        "version_date_text": v_date_str,
        "article_no": art_no,
        "article_no_raw": art_raw,
        "action_type": action_type,
        "content": '\n'.join(content_lines).strip(),
        "reason": '\n'.join(reason_lines).strip(),
        "comparison_url": comparison_url,
        "source": "立法院法律系統",
        "source_url": source_url,
        "raw_path": raw_path
    }
