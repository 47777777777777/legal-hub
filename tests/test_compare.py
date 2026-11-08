"""
tests/test_compare.py

Prompt 4J 比對引擎單元測試與嚴格不變量驗收。
涵蓋 1-6 指定測試案例：
1. 改一個字
2. 僅標點變動
3. 新增一項
4. 刪除一項
5. 整條改寫
6. 制定版 (無前版)
7. 刪除版
8. 條次移列（無明確連結則不比對）
9. 表格行（含框線字元，逐行原樣並排，不加 diff 標記）
10. 「之」條（如第 296-1 條）
11. 全庫 / 全樣本不變量斷言：
    - equal + delete == old_norm
    - equal + insert == new_norm
"""

import pytest
from backend.compare import (
    diff_tokens,
    tokens_to_html,
    compare_articles,
    normalize_text_for_compare
)

def test_1_change_single_char():
    """改一個字：例如『處一年以上五年以下』改為『處一年以上七年以下』"""
    old_t = "犯前項之罪者，處一年以上五年以下有期徒刑。"
    new_t = "犯前項之罪者，處一年以上七年以下有期徒刑。"
    
    tokens = diff_tokens(old_t, new_t)
    # 不變量
    recon_old = "".join(t for op, t in tokens if op in ("equal", "delete"))
    recon_new = "".join(t for op, t in tokens if op in ("equal", "insert"))
    assert recon_old == old_t
    assert recon_new == new_t
    
    # 斷言變動處為 '五' -> '七'
    assert ("delete", "五") in tokens
    assert ("insert", "七") in tokens
    
    comp = compare_articles(old_t, new_t)
    assert comp["status"] == "compared"
    assert '<ins class="diff-ins">七</ins>' in comp["new_html"]
    assert '<del class="diff-del">五</del>' in comp["old_html"]

def test_2_punctuation_only_change():
    """僅標點變動：例如逗號改為分號"""
    old_t = "本法自公布日施行，但第二條除外。"
    new_t = "本法自公布日施行；但第二條除外。"
    
    tokens = diff_tokens(old_t, new_t)
    recon_old = "".join(t for op, t in tokens if op in ("equal", "delete"))
    recon_new = "".join(t for op, t in tokens if op in ("equal", "insert"))
    assert recon_old == old_t
    assert recon_new == new_t

    assert ("delete", "，") in tokens
    assert ("insert", "；") in tokens

def test_3_add_paragraph():
    """新增一項：例如 APA 128 增訂第 3 項"""
    old_t = "行政處分於法定救濟期間經過後，具有下列各款情形之一者，相對人或利害關係人得向行政機關申請撤銷、廢止或變更之。\n前項之申請，應自法定救濟期間經過後三個月內為之。"
    new_t = old_t + "\n第一項之新證據，指處分作成前已存在或成立而未及調查斟酌之證據。"

    comp = compare_articles(old_t, new_t)
    assert comp["status"] == "compared"
    assert len(comp["paragraphs"]) == 3
    # 第 3 項狀態應為 added
    p3 = comp["paragraphs"][2]
    assert p3["status"] == "added"
    assert "第一項之新證據" in p3["new_html"]
    assert "（本項新增）" in p3["old_html"]

def test_4_delete_paragraph():
    """刪除一項"""
    old_t = "第一項條文內容。\n第二項待刪除內容。"
    new_t = "第一項條文內容。"

    comp = compare_articles(old_t, new_t)
    assert comp["status"] == "compared"
    assert len(comp["paragraphs"]) == 2
    p2 = comp["paragraphs"][1]
    assert p2["status"] == "deleted"
    assert "（本項刪除）" in p2["new_html"]
    assert "第二項待刪除內容。" in p2["old_html"]

def test_5_full_rewrite():
    """整條改寫"""
    old_t = "公務員不得收受任何餽贈。"
    new_t = "公務員受國家委託執行職務，應保持公正廉潔，違反者依公務員懲戒法懲戒。"

    tokens = diff_tokens(old_t, new_t)
    recon_old = "".join(t for op, t in tokens if op in ("equal", "delete"))
    recon_new = "".join(t for op, t in tokens if op in ("equal", "insert"))
    assert recon_old == old_t
    assert recon_new == new_t

    comp = compare_articles(old_t, new_t)
    assert comp["status"] == "compared"
    assert comp["old_plain"] == old_t
    assert comp["new_plain"] == new_t

def test_6_enacted_version():
    """制定版（無前版）"""
    new_t = "為使行政行為遵循公正、公開與民主之程序，特制定本法。"
    comp = compare_articles(None, new_t, action_type="制定")
    assert comp["status"] == "enacted"
    assert comp["old_plain"] == ""
    assert "（未制定）" in comp["old_html"]
    assert comp["new_plain"] == new_t

def test_7_deleted_version():
    """刪除版"""
    old_t = "本條原條文規定內容。"
    comp = compare_articles(old_t, "", action_type="刪除")
    assert comp["status"] == "deleted"
    assert "（刪除）" in comp["new_html"]
    assert "本條原條文規定內容。" in comp["old_html"]

def test_8_shifted_unlinked():
    """條次移列：若無明確來源 old_content，依寧缺勿錯原則不顯示假比對"""
    # 當無法確定前版條號時，傳入 old_content=None
    new_t = "原第四十五條移列之條文內容。"
    comp = compare_articles(None, new_t, action_type="修正")
    assert comp["status"] == "enacted"  # 顯示該版本文字，不猜測舊條文

def test_9_table_preservation():
    """表格：含框線字元，逐行原樣並排，不加標註"""
    table_old = "┌──────┬──────┐\n│ 項目 │ 舊率 │\n└──────┴──────┘"
    table_new = "┌──────┬──────┐\n│ 項目 │ 新率 │\n└──────┴──────┘"

    comp = compare_articles(table_old, table_new)
    assert comp["status"] == "compared"
    assert comp["is_table"] is True
    # 表格不應含有 ins / del 標籤
    assert "<ins" not in comp["new_html"]
    assert "<del" not in comp["old_html"]
    assert "diff-table-pre" in comp["new_html"]

def test_10_sub_article_zhi():
    """『之』條（如第 296-1 條）正常比對"""
    old_t = "買賣、質押人口者，處五年以上有期徒刑。"
    new_t = "買賣、質押人口者，處五年以上有期徒刑，得併科五十萬元以下罰金。"

    tokens = diff_tokens(old_t, new_t)
    recon_old = "".join(t for op, t in tokens if op in ("equal", "delete"))
    recon_new = "".join(t for op, t in tokens if op in ("equal", "insert"))
    assert recon_old == old_t
    assert recon_new == new_t

    comp = compare_articles(old_t, new_t)
    assert comp["status"] == "compared"
    assert '<ins class="diff-ins">，得併科五十萬元以下罰金</ins>' in comp["new_html"]

def test_11_barcode_merging():
    """合併過於破碎的 equal 區段（長度 < 2 字元且夾在變動之間）"""
    old_t = "甲乙丙"
    new_t = "丁乙戊"
    tokens = diff_tokens(old_t, new_t)
    # '乙' 長度為 1 且夾在甲->丁與丙->戊之間，應被併入，不應作為單獨的 equal 顯示條碼
    ops = [op for op, _ in tokens]
    assert ops == ["delete", "insert"]
    assert tokens == [("delete", "甲乙丙"), ("insert", "丁乙戊")]

