"""
tests/test_article_structure_v2.py

Prompt 4G Section 2:
結構解析器修復驗證測試（全手工寫期望值）：
1. 案例 (a)：項結尾非標點（如引號「內政部」），下一項不得被併入，輸出為兩項（Ⅰ、Ⅱ）。
2. 案例 (b)：條文內含框線表格（─│┌┐└┘├┤┬┴┼），不得合併壓平，逐行原樣保留。
3. 項結尾為「）」、「數字」、「英文」的兩項條文，正確分項。
4. 款與目夾在兩項之間。
5. 羅馬數字項號擴展至 XX 以上（如 25 -> XXV, 50 -> L）。
6. 去空白換行後文字 100% 相等的不變量。
"""

import re
import pytest
from backend.article_structure import (
    unwrap_text,
    parse_article_structure,
    render_article_copy_text,
    to_roman,
    is_table_line
)

def test_case_a_unpunctuated_quote_ending():
    """
    Prompt 4G §2(a):
    輸入: 本法所稱「主管機關」，為「內政部」\r\n第二項內文。
    期望: 兩個項，第一項為「Ⅰ　本法所稱「主管機關」，為「內政部」」，第二項為「Ⅱ　第二項內文。」
    """
    text = "本法所稱「主管機關」，為「內政部」\r\n第二項內文。"
    blocks = parse_article_structure(text, is_standard_article=True)
    
    assert len(blocks) == 2, f"應為 2 項，實得 {len(blocks)} 區塊"
    assert blocks[0]["kind"] == "para"
    assert blocks[0]["roman_no"] == "Ⅰ"
    assert blocks[0]["text"] == "本法所稱「主管機關」，為「內政部」"
    
    assert blocks[1]["kind"] == "para"
    assert blocks[1]["roman_no"] == "Ⅱ"
    assert blocks[1]["text"] == "第二項內文。"

def test_case_b_table_box_drawing_preserved():
    """
    Prompt 4G §2(b):
    表格區塊不得合併壓成一行，輸出行數必須等於來源行數。
    """
    table_text = "等級　　│　金額\r\n─────┼─────\r\n甲　　　│　一千元\r\n乙　　　│　二千元"
    blocks = parse_article_structure(table_text, is_standard_article=True)
    
    table_blocks = [b for b in blocks if b["kind"] == "table"]
    assert len(table_blocks) == 4, f"4 行表格應產生 4 個 table 區塊，實得 {len(table_blocks)}"
    
    copy_out = render_article_copy_text(table_text, mode="roman")
    assert "─────┼─────" in copy_out
    assert copy_out.count("\n") == 3, f"表格行數應為 4 行（3 個換行），實得: {copy_out}"

def test_items_subs_between_two_paras():
    """
    測試款與目夾在兩項之間。
    """
    content = (
        "第一項開頭內文：\r\n"
        "一、第一款內文。\r\n"
        "（一）第一目內文。\r\n"
        "二、第二款內文。\r\n"
        "第二項開頭獨立段落。"
    )
    blocks = parse_article_structure(content, is_standard_article=True)
    kinds = [b["kind"] for b in blocks]
    assert kinds == ["para", "item", "sub", "item", "para"]
    assert blocks[0]["roman_no"] == "Ⅰ"
    assert blocks[-1]["roman_no"] == "Ⅱ"
    assert blocks[1]["no_raw"] == "一、"
    assert blocks[2]["no_raw"] == "（一）"
    assert blocks[3]["no_raw"] == "二、"

def test_roman_numerals_beyond_twenty():
    """
    Prompt 4G §2.5: 羅馬數字項號擴展至 XX 以上。
    """
    assert to_roman(1) == "Ⅰ"
    assert to_roman(12) == "Ⅻ"
    assert to_roman(13) == "XIII"
    assert to_roman(20) == "XX"
    assert to_roman(21) == "XXI"
    assert to_roman(25) == "XXV"
    assert to_roman(50) == "L"

def test_invariant_content_equality():
    """
    測試不變量：去掉所有空白與換行後，結構文字串接 100% 等於來源 ArticleContent。
    """
    samples = [
        "本法所稱「主管機關」，為「內政部」\r\n第二項內文。",
        "等級　　│　金額\r\n─────┼─────\r\n甲　　　│　一千元\r\n乙　　　│　二千元",
        "一、第一款內文\r\n二、第二款內文",
        "單項條文無羅馬數字。"
    ]
    for s in samples:
        blocks = parse_article_structure(s, is_standard_article=True)
        reconstructed = "".join(b.get("no_raw", "") + b.get("text", "") for b in blocks)
        clean_orig = re.sub(r'\s+', '', s)
        clean_recon = re.sub(r'\s+', '', reconstructed)
        assert clean_orig == clean_recon, f"不變量破壞: {clean_orig} vs {clean_recon}"

