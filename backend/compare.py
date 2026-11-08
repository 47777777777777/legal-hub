"""
backend/compare.py

自動自製修正對照表（標示修改處）比對引擎。
嚴格依據 Prompt 4J 規格實作：
1. 資料來源：以 LIS 已入庫的 article_versions 逐字文字為準。
   修正前條文 = 同一條的前一個版本的逐字文字。
2. 決定性字元比對：使用 difflib.SequenceMatcher(autojunk=False)，
   合併長度 < 2 字元且夾在變動之間的 equal 區段，避免條碼效應。
3. 全庫嚴格不變量 (Invariant)：
   - equal + delete 串接 100% 等於前版文字（正規化空白後）
   - equal + insert 串接 100% 等於後版文字（正規化空白後）
4. 表格行（含框線字元）不比對，逐行原樣並排顯示。
5. 項結構並排：利用 backend/article_structure.py 區塊對齊，項數不同時新增項整段標示。
"""

import difflib
import html
import re
from typing import List, Dict, Any, Tuple, Optional
from backend.article_structure import parse_article_structure, is_table_line, unwrap_text

def normalize_text_for_compare(text: str) -> str:
    """
    將條文文字依結構規則進行決定性正規化：
    - 呼叫 unwrap_text 合併硬折行
    - 去除每行首尾空白與多餘空行
    - 統一換行符號為 '\n'
    """
    if not text:
        return ""
    unwrapped = unwrap_text(text, is_standard_article=True)
    lines = [l.strip() for l in unwrapped.splitlines() if l.strip()]
    return "\n".join(lines)

def diff_tokens(old_text: str, new_text: str) -> List[Tuple[str, str]]:
    """
    對兩段文字進行決定性字元比對，並合併長度 < 2 的破碎 equal 區段。
    回傳: [('equal' | 'delete' | 'insert', text), ...]
    保證嚴格滿足不變量：
      equal + delete == old_text
      equal + insert == new_text
    """
    old_norm = normalize_text_for_compare(old_text)
    new_norm = normalize_text_for_compare(new_text)

    if not old_norm and not new_norm:
        return []
    if not old_norm:
        return [("insert", new_norm)]
    if not new_norm:
        return [("delete", old_norm)]

    matcher = difflib.SequenceMatcher(None, old_norm, new_norm, autojunk=False)
    raw_ops = matcher.get_opcodes()

    # Step 1: 展開為基礎 tokens
    tokens = []
    for tag, i1, i2, j1, j2 in raw_ops:
        if tag == "equal":
            tokens.append(("equal", old_norm[i1:i2]))
        elif tag == "delete":
            tokens.append(("delete", old_norm[i1:i2]))
        elif tag == "insert":
            tokens.append(("insert", new_norm[j1:j2]))
        elif tag == "replace":
            tokens.append(("delete", old_norm[i1:i2]))
            tokens.append(("insert", new_norm[j1:j2]))

    # Step 2: 組織為變動區塊與相等區塊
    blocks = []
    for op, text in tokens:
        if op == "equal":
            blocks.append({"type": "equal", "text": text})
        else:
            if blocks and blocks[-1]["type"] == "change":
                blocks[-1]["ops"].append((op, text))
            else:
                blocks.append({"type": "change", "ops": [(op, text)]})

    # Step 3: 合併長度 < 2 且夾在變動之間的 equal 區段
    merged_blocks = []
    i = 0
    while i < len(blocks):
        b = blocks[i]
        if b["type"] == "equal" and len(b["text"]) < 2 and 0 < i < len(blocks) - 1:
            eq_text = b["text"]
            prev_change = merged_blocks[-1]
            next_change = blocks[i + 1]
            prev_change["ops"].append(("delete", eq_text))
            prev_change["ops"].append(("insert", eq_text))
            prev_change["ops"].extend(next_change["ops"])
            i += 2  # 跳過當前 equal 與後續 next_change
        else:
            merged_blocks.append(b)
            i += 1

    # Step 4: 展平成最終 tokens 並合併相鄰相同運算子
    final_tokens = []
    for b in merged_blocks:
        if b["type"] == "equal":
            final_tokens.append(("equal", b["text"]))
        else:
            cur_del = []
            cur_ins = []
            for op, text in b["ops"]:
                if op == "delete":
                    cur_del.append(text)
                elif op == "insert":
                    cur_ins.append(text)
            if cur_del:
                final_tokens.append(("delete", "".join(cur_del)))
            if cur_ins:
                final_tokens.append(("insert", "".join(cur_ins)))

    # Step 5: 不變量斷言驗證
    recon_old = "".join(t for op, t in final_tokens if op in ("equal", "delete"))
    recon_new = "".join(t for op, t in final_tokens if op in ("equal", "insert"))
    if recon_old != old_norm:
        raise ValueError(f"Invariant violation (old): recon='{recon_old}' != norm='{old_norm}'")
    if recon_new != new_norm:
        raise ValueError(f"Invariant violation (new): recon='{recon_new}' != norm='{new_norm}'")

    return final_tokens

def tokens_to_html(tokens: List[Tuple[str, str]], target: str) -> str:
    """
    將 diff tokens 轉換為安全標註的 HTML：
    - target == "new": 輸出修正條文 (新增處使用 <ins class="diff-ins">...</ins>)
    - target == "old": 輸出修正前條文 (刪除處使用 <del class="diff-del">...</del>)
    """
    res = []
    for op, text in tokens:
        escaped = html.escape(text)
        if target == "new":
            if op == "equal":
                res.append(escaped)
            elif op == "insert":
                res.append(f'<ins class="diff-ins">{escaped}</ins>')
        elif target == "old":
            if op == "equal":
                res.append(escaped)
            elif op == "delete":
                res.append(f'<del class="diff-del">{escaped}</del>')
    return "".join(res)

def compare_articles(
    old_content: Optional[str],
    new_content: str,
    action_type: str = "修正"
) -> Dict[str, Any]:
    """
    比對條文版本結構並產出兩欄並排資料：
    回傳字典結構：
      {
        "status": "compared" | "enacted" | "deleted" | "unlinked",
        "status_label": str,
        "is_table": bool,
        "col_new_title": "修正條文",
        "col_old_title": "現行條文",
        "new_plain": str,
        "old_plain": str,
        "new_html": str,
        "old_html": str,
        "paragraphs": List[Dict], # 項對齊結構
        "tokens": List[Tuple[str, str]]
      }
    """
    # 檢查刪除或未連結
    if action_type == "刪除" or (new_content and "（刪除）" in new_content and not old_content):
        old_norm = normalize_text_for_compare(old_content or "")
        return {
            "status": "deleted",
            "status_label": "刪除",
            "is_table": False,
            "col_new_title": "修正條文",
            "col_old_title": "現行條文",
            "new_plain": "（刪除）",
            "old_plain": old_norm,
            "new_html": '<span class="diff-deleted-note">（刪除）</span>',
            "old_html": f'<del class="diff-del">{html.escape(old_norm)}</del>' if old_norm else "",
            "paragraphs": [],
            "tokens": [("delete", old_norm)] if old_norm else []
        }

    # 制定或新增（無前一版）
    if not old_content:
        new_norm = normalize_text_for_compare(new_content)
        return {
            "status": "enacted",
            "status_label": "制定／新增（無修正前條文）",
            "is_table": any(is_table_line(l) for l in new_content.splitlines()),
            "col_new_title": "修正條文",
            "col_old_title": "現行條文",
            "new_plain": new_norm,
            "old_plain": "",
            "new_html": html.escape(new_norm),
            "old_html": '<span class="diff-none-note">（未制定）</span>',
            "paragraphs": [],
            "tokens": [("insert", new_norm)]
        }

    # 檢查是否包含製表框線字元（表格不比對，逐行原樣並排）
    old_has_table = any(is_table_line(l) for l in old_content.splitlines())
    new_has_table = any(is_table_line(l) for l in new_content.splitlines())
    if old_has_table or new_has_table:
        old_lines = [l for l in old_content.splitlines() if l.strip()]
        new_lines = [l for l in new_content.splitlines() if l.strip()]
        return {
            "status": "compared",
            "status_label": "表格比對（逐行並排，不加標註）",
            "is_table": True,
            "col_new_title": "修正條文",
            "col_old_title": "現行條文",
            "new_plain": "\n".join(new_lines),
            "old_plain": "\n".join(old_lines),
            "new_html": "<pre class=\"diff-table-pre\">" + html.escape("\n".join(new_lines)) + "</pre>",
            "old_html": "<pre class=\"diff-table-pre\">" + html.escape("\n".join(old_lines)) + "</pre>",
            "paragraphs": [],
            "tokens": []
        }

    # 正常文字比對
    old_norm = normalize_text_for_compare(old_content)
    new_norm = normalize_text_for_compare(new_content)
    tokens = diff_tokens(old_norm, new_norm)

    # 依項結構拆解並排
    old_blocks = parse_article_structure(old_content, is_standard_article=True)
    new_blocks = parse_article_structure(new_content, is_standard_article=True)

    # 以項 (para_idx) 為單位分組
    def group_by_para(blocks):
        paras = {}
        for b in blocks:
            p_idx = max(1, b.get("para_idx", 1))
            paras.setdefault(p_idx, []).append(b)
        return paras

    old_paras = group_by_para(old_blocks)
    new_paras = group_by_para(new_blocks)
    all_para_keys = sorted(set(list(old_paras.keys()) + list(new_paras.keys())))

    aligned_paragraphs = []
    for p_idx in all_para_keys:
        o_list = old_paras.get(p_idx, [])
        n_list = new_paras.get(p_idx, [])

        o_text = "\n".join(f"{b.get('no_raw','')}{b.get('text','')}" for b in o_list)
        n_text = "\n".join(f"{b.get('no_raw','')}{b.get('text','')}" for b in n_list)

        o_norm = normalize_text_for_compare(o_text)
        n_norm = normalize_text_for_compare(n_text)

        if o_norm and n_norm:
            p_tokens = diff_tokens(o_norm, n_norm)
            p_new_html = tokens_to_html(p_tokens, "new")
            p_old_html = tokens_to_html(p_tokens, "old")
            p_status = "modified" if any(op != "equal" for op, _ in p_tokens) else "unchanged"
        elif not o_norm and n_norm:
            p_tokens = [("insert", n_norm)]
            p_new_html = f'<ins class="diff-ins">{html.escape(n_norm)}</ins>'
            p_old_html = '<span class="diff-none-note">（本項新增）</span>'
            p_status = "added"
        elif o_norm and not n_norm:
            p_tokens = [("delete", o_norm)]
            p_new_html = '<span class="diff-none-note">（本項刪除）</span>'
            p_old_html = f'<del class="diff-del">{html.escape(o_norm)}</del>'
            p_status = "deleted"
        else:
            continue

        aligned_paragraphs.append({
            "para_idx": p_idx,
            "status": p_status,
            "new_html": p_new_html,
            "old_html": p_old_html,
            "new_plain": n_norm,
            "old_plain": o_norm
        })

    return {
        "status": "compared",
        "status_label": "比對完成",
        "is_table": False,
        "col_new_title": "修正條文",
        "col_old_title": "現行條文",
        "new_plain": new_norm,
        "old_plain": old_norm,
        "new_html": tokens_to_html(tokens, "new"),
        "old_html": tokens_to_html(tokens, "old"),
        "paragraphs": aligned_paragraphs,
        "tokens": tokens
    }

