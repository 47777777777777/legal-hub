"""
backend/article_structure.py
嚴格依據中央法規標準法第 8 條「條、項、款、目」體系與全庫普查實證資料之結構解析模組。
- 項 (para): 實質獨立段落，僅當條文具有 ≥ 2 個項時冠金色羅馬項號 (Ⅰ, Ⅱ, Ⅲ...)；單項條文不冠。
- 款 (item): 隸屬於項之列舉條目 (一、, 二、, 十一、)。
- 目 (sub): 隸屬於款之次細目 (（一）, （二）)。
- 細目 (sub_sub): 隸屬於目之子細目 (1., １、, (1))。
- 續行 (continuation): 原始折行由空白或標點符號起首、或前行未結句者，於顯示層接合，不變更原儲存文字。
- 不變量 (Invariant): 去掉所有空白換行後，結構文字串接 100% 等於來源 ArticleContent。
"""

import re
from typing import List, Dict, Any

RE_SPACES = re.compile(r'^[ \t　]+')
RE_PUNCT = re.compile(r'^[，。、；：！？」』）\),\.．]')
RE_KUAN = re.compile(r'^([一二三四五六七八九十百]+、)\s*')
RE_MU = re.compile(r'^([（(][一二三四五六七八九十百]+[）)])\s*')
RE_SUBMU = re.compile(r'^([0-9０-９]+[.．、]|\([0-9０-９]+\)|（[0-9０-９]+）)\s*')

ROMAN_NUMERALS = [
    "", "Ⅰ", "Ⅱ", "Ⅲ", "Ⅳ", "Ⅴ", "Ⅵ", "Ⅶ", "Ⅷ", "Ⅸ", "Ⅹ",
    "Ⅺ", "Ⅻ", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX"
]

def parse_article_structure(content: str, is_standard_article: bool = True) -> List[Dict[str, Any]]:
    """
    將原始 ArticleContent 解析為語意結構區塊陣列。
    每個區塊結構:
      {
        "kind": "para" | "item" | "sub" | "sub_sub",
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

        if not merged:
            merged.append(trimmed)
            continue

        prev = merged[-1]
        prev_ends = bool(re.search(r'[。：；！？:;]$', prev))

        if (has_spaces and not is_sub) or starts_with_punct or (not prev_ends and not is_sub):
            # 接續行：直接接合至前行末尾
            merged[-1] += trimmed
        else:
            merged.append(trimmed)

    # Step 2: 結構區塊辨識 (項、款、目、細目)
    blocks = []
    para_count = 0
    for line in merged:
        m_kuan = RE_KUAN.match(line)
        m_mu = RE_MU.match(line)
        m_submu = RE_SUBMU.match(line)

        if m_kuan:
            marker = m_kuan.group(1)
            text = line[len(marker):].strip()
            blocks.append({
                "kind": "item",
                "no_raw": marker,
                "text": text,
                "para_idx": para_count
            })
        elif m_mu:
            marker = m_mu.group(1)
            text = line[len(marker):].strip()
            blocks.append({
                "kind": "sub",
                "no_raw": marker,
                "text": text,
                "para_idx": para_count
            })
        elif m_submu:
            marker = m_submu.group(1)
            text = line[len(marker):].strip()
            blocks.append({
                "kind": "sub_sub",
                "no_raw": marker,
                "text": text,
                "para_idx": para_count
            })
        else:
            # 實質獨立項 (Paragraph)
            para_count += 1
            blocks.append({
                "kind": "para",
                "no_raw": "",
                "text": line,
                "para_idx": para_count
            })

    # Step 3: 羅馬數字指派 (嚴格遵循：僅當為標準「條」法規且 ≥ 2 個項時才編羅馬數字；款號開頭無前項者或非標準法規不冠)
    for b in blocks:
        if b["kind"] == "para":
            idx = b.get("para_idx", 0)
            if is_standard_article and para_count >= 2 and 0 < idx < len(ROMAN_NUMERALS):
                b["roman_no"] = ROMAN_NUMERALS[idx]
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
    else:
        body = f"{no_raw}{text}"

    return f"{header}\n{body}".strip() if header else body
