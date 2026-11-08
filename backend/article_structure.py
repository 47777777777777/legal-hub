"""
backend/article_structure.py
嚴格依據中央法規標準法第 8 條「條、項、款、目」體系與全庫普查實證資料之結構解析模組。
- 項 (para): 實質獨立段落，僅當條文具有 ≥ 2 個項時冠金色羅馬項號 (Ⅰ, Ⅱ, Ⅲ...)；單項條文不冠。
- 款 (item): 隸屬於項之列舉條目 (一、, 二、, 十一、)。
- 目 (sub): 隸屬於款之次細目 (（一）, （二）)。
- 細目 (sub_sub): 隸屬於目之子細目 (1., １、, (1))。
- 表格 (table): 含框線字元之區塊，逐行原樣保留，不合併、不冠項號，支援等寬與逐行原樣複製。
- 續行 (continuation): 依據明確接續證據（行首縮排、行首標點、前行末尾逗號/分號）接合，不變更原儲存文字。
- 不變量 (Invariant):
  1. 去掉所有空白換行後，結構文字串接 100% 等於來源 ArticleContent。
  2. 含框線字元的表格行，輸出行數 100% 等於來源行數。
"""

import re
from typing import List, Dict, Any, Optional

RE_SPACES = re.compile(r'^[ \t　]+')
RE_PUNCT = re.compile(r'^[，。、；：！？」』）\),\.．%％]')
RE_CONTINUATION_PREV = re.compile(r'[，、；,-]$')
RE_KUAN = re.compile(r'^([一二三四五六七八九十百]+、)\s*')
RE_MU = re.compile(r'^([（(][一二三四五六七八九十百]+[）)])\s*')
RE_SUBMU = re.compile(r'^([0-9０-９]+[.．、]|\([0-9０-９]+\)|（[0-9０-９]+）)\s*')

BOX_DRAWING_CHARS = set("─│┌┐└┘├┤┬┴┼═║╒╓╔╕╖╗╘╙╚╛╜╝╞╟╠╡╢╣╤╥╦╧╨╩╪╫╬╱╲╳")

UNICODE_ROMANS = [
    "", "Ⅰ", "Ⅱ", "Ⅲ", "Ⅳ", "Ⅴ", "Ⅵ", "Ⅶ", "Ⅷ", "Ⅸ", "Ⅹ", "Ⅺ", "Ⅻ"
]

def to_roman(n: int) -> str:
    """產生羅馬數字項號（支援無限數值，1~12 使用 Unicode 專用字元 Ⅰ~Ⅻ，13 以上動態生成）"""
    if n <= 0:
        return ""
    if n < len(UNICODE_ROMANS):
        return UNICODE_ROMANS[n]
    
    val_map = [
        (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
        (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
        (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")
    ]
    res = []
    rem = n
    for val, sym in val_map:
        while rem >= val:
            res.append(sym)
            rem -= val
    return "".join(res)

def is_table_line(line: str) -> bool:
    """判斷該行是否包含製表框線字元"""
    return any(c in BOX_DRAWING_CHARS for c in line)

def unwrap_text(text: str, is_standard_article: bool = True) -> str:
    """
    顯示層接續行合併 (Display-layer Unwrap)：
    僅依據來源本身的明確續行證據（行首縮排、行首標點、前行末尾逗號/分號）合併。
    非標準條號法規（如動員戡亂時期臨時條款）來源每行硬折行，非款非目行一律自動續行。
    表格行（含框線字元）絕對不合併，保持逐行原樣。
    """
    if not text:
        return ""
    raw_lines = text.splitlines()
    clean_lines = [l for l in raw_lines if l.strip()]
    if not clean_lines:
        return ""
        
    merged = []
    for line in clean_lines:
        trimmed = line.strip()
        is_sub = bool(RE_KUAN.match(trimmed) or RE_MU.match(trimmed) or RE_SUBMU.match(trimmed))
        starts_with_punct = bool(RE_PUNCT.match(trimmed))
        has_spaces = bool(RE_SPACES.match(line))
        is_curr_table = is_table_line(line)
        
        if not merged:
            merged.append(line if is_curr_table else trimmed)
            continue
            
        prev = merged[-1]
        is_prev_table = is_table_line(prev)
        prev_is_continuation = bool(RE_CONTINUATION_PREV.search(prev.rstrip()))
        
        # 嚴格續行判斷：
        # 當前行與前行皆非表格行，且當前行不是款/目/細目起首，且符合續行條件
        can_merge = (
            not is_curr_table and
            not is_prev_table and
            not is_sub and
            (
                (has_spaces and not is_sub) or
                starts_with_punct or
                prev_is_continuation or
                (not is_standard_article and not is_sub)
            )
        )
        
        if can_merge:
            merged[-1] += trimmed
        else:
            merged.append(line if is_curr_table else trimmed)
            
    return "\n".join(merged)

def parse_article_structure(content: str, is_standard_article: bool = True) -> List[Dict[str, Any]]:
    """
    將原始 ArticleContent 解析為語意結構區塊陣列。
    每個區塊結構:
      {
        "kind": "para" | "item" | "sub" | "sub_sub" | "table",
        "no_raw": str,      # 款號/目號原文 (如 "一、", "（一）", "1.")
        "roman_no": str,    # 羅馬數字項號 (如 "Ⅰ", "Ⅱ")，單項條文為 ""
        "text": str,        # 內文文字 (已去除 marker)
        "para_idx": int     # 第幾項 (1-based)
      }
    """
    if not content:
        return []

    raw_lines = content.splitlines()
    clean_lines = [l for l in raw_lines if l.strip()]
    if not clean_lines:
        return []

    # Step 1: 接續行自動合併 (Display-layer Unwrap)
    merged = []
    for line in clean_lines:
        trimmed = line.strip()
        is_sub = bool(RE_KUAN.match(trimmed) or RE_MU.match(trimmed) or RE_SUBMU.match(trimmed))
        starts_with_punct = bool(RE_PUNCT.match(trimmed))
        has_spaces = bool(RE_SPACES.match(line))
        is_curr_table = is_table_line(line)

        if not merged:
            merged.append(line if is_curr_table else trimmed)
            continue

        prev = merged[-1]
        is_prev_table = is_table_line(prev)
        prev_is_continuation = bool(RE_CONTINUATION_PREV.search(prev.rstrip()))

        can_merge = (
            not is_curr_table and
            not is_prev_table and
            not is_sub and
            (
                (has_spaces and not is_sub) or
                starts_with_punct or
                prev_is_continuation or
                (not is_standard_article and not is_sub)
            )
        )

        if can_merge:
            merged[-1] += trimmed
        else:
            merged.append(line if is_curr_table else trimmed)

    # Step 2: 結構區塊辨識 (項、款、目、細目、表格)
    blocks = []
    para_count = 0
    for line in merged:
        if is_table_line(line):
            # 表格行原樣保留
            blocks.append({
                "kind": "table",
                "no_raw": "",
                "roman_no": "",
                "text": line,
                "para_idx": 0
            })
            continue

        m_kuan = RE_KUAN.match(line)
        m_mu = RE_MU.match(line)
        m_submu = RE_SUBMU.match(line)

        if m_kuan:
            marker = m_kuan.group(1)
            text = line[len(marker):].strip()
            blocks.append({
                "kind": "item",
                "no_raw": marker,
                "roman_no": "",
                "text": text,
                "para_idx": para_count
            })
        elif m_mu:
            marker = m_mu.group(1)
            text = line[len(marker):].strip()
            blocks.append({
                "kind": "sub",
                "no_raw": marker,
                "roman_no": "",
                "text": text,
                "para_idx": para_count
            })
        elif m_submu:
            marker = m_submu.group(1)
            text = line[len(marker):].strip()
            blocks.append({
                "kind": "sub_sub",
                "no_raw": marker,
                "roman_no": "",
                "text": text,
                "para_idx": para_count
            })
        else:
            # 實質獨立項 (Paragraph)
            para_count += 1
            blocks.append({
                "kind": "para",
                "no_raw": "",
                "roman_no": "",
                "text": line,
                "para_idx": para_count
            })

    # Step 3: 羅馬數字項號指派 (嚴格遵循：僅當為標準「條」法規且 ≥ 2 個項時才編羅馬數字；單項不編)
    for b in blocks:
        if b["kind"] == "para":
            idx = b.get("para_idx", 0)
            if is_standard_article and para_count >= 2 and idx > 0:
                b["roman_no"] = to_roman(idx)
            else:
                b["roman_no"] = ""
        else:
            b["roman_no"] = ""

    return blocks

def render_article_copy_text(content: str, mode: str = "plain", label_raw: str = "", act_name: str = "") -> str:
    """
    產生條文複製文字。
    mode:
      - 'plain': 輸出來源 ArticleContent 原樣 (不含羅馬數字、不改動換行)
      - 'roman': 輸出結構化文字 (項冠羅馬數字、款目縮排；僅 ≥ 2 項有羅馬數字)
      - 'label': 輸出項標籤文字 (項冠「第 1 項　...」；僅 ≥ 2 項有標籤)
    """
    if mode == "plain":
        # 來源純文字原樣輸出
        header = f"{act_name} {label_raw}".strip() if (act_name or label_raw) else ""
        return f"{header}\n{content}".strip() if header else content

    is_standard = bool(label_raw)
    blocks = parse_article_structure(content, is_standard_article=is_standard)
    lines = []
    header = f"{act_name} {label_raw}".strip() if (act_name or label_raw) else ""
    if header:
        lines.append(header)

    para_count = len([b for b in blocks if b["kind"] == "para"])
    for b in blocks:
        kind = b["kind"]
        roman = b.get("roman_no", "")
        no_raw = b.get("no_raw", "")
        text = b.get("text", "")
        para_idx = b.get("para_idx", 0)

        if kind == "para":
            if mode == "roman":
                prefix = f"{roman}　" if roman else ""
                lines.append(f"{prefix}{text}")
            elif mode == "label":
                prefix = f"第 {para_idx} 項　" if (is_standard and para_count >= 2 and para_idx) else ""
                lines.append(f"{prefix}{text}")
            else:
                lines.append(text)
        elif kind == "item":
            lines.append(f"　　{no_raw}{text}")
        elif kind == "sub":
            lines.append(f"　　　　{no_raw}{text}")
        elif kind == "sub_sub":
            lines.append(f"　　　　　　{no_raw}{text}")
        elif kind == "table":
            lines.append(text)

    return "\n".join(lines)

def render_single_block_copy(block: Dict[str, Any], label_raw: str = "", act_name: str = "") -> str:
    """
    點擊單一區塊複製該區塊內容。
    標頭行 (法規名稱與條標示) 僅使用 label_raw；沒有條標示的法規不得補「第 N 條」。
    """
    header = f"{act_name} {label_raw}".strip() if (act_name or label_raw) else ""
    kind = block.get("kind", "para")
    roman = block.get("roman_no", "")
    no_raw = block.get("no_raw", "")
    text = block.get("text", "")

    body = ""
    if kind == "para":
        prefix = f"{roman}　" if roman else ""
        body = f"{prefix}{text}"
    elif kind == "table":
        body = text
    else:
        body = f"{no_raw}{text}"

    return f"{header}\n{body}".strip() if header else body
