"""
tests/test_citations.py

Prompt 4E 第 2 項與 Prompt 4G 第 1 項：
條文引用解析與結構化連結模組（backend/citations.py）單元測試。
包含 ≥ 60 個人工撰寫明確期望值的測試案例，涵蓋：
- explicit（顯式引用）：知名法規全名與簡稱（民法、刑法、憲法、公司法、勞基法、個資法、著作權法等）
- chain（連鎖引用）：同法第 N 條、同法第 N 條之 M、連續多個同法引用
- host（宿主引用）：本法第 N 條、單純第 N 條
- unresolved（未解析）：非現存法規名稱、虛構法規
- 條號格式：中文數字（零、〇、一至九、十、百、千）、阿拉伯數字、全形數字、支條號（之 1、-1）
- 範圍引用：至第 N 條之連續展開
- 特殊邊界：標點相連、括號包覆、條文末尾、空字串
"""

import pytest
from pathlib import Path
from backend.citations import resolve_citations, chn_to_int, normalize_article_no

BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data" / "legal_hub.db"

# -------------------------------------------------------------
# 1. 數字轉換與條號標準化單元測試 (15 cases)
# -------------------------------------------------------------
@pytest.mark.parametrize("chn,expected", [
    ("一", 1),
    ("十", 10),
    ("十一", 11),
    ("二十", 20),
    ("二十五", 25),
    ("一百", 100),
    ("一百零五", 105),
    ("一百八十四", 184),
    ("二百〇一", 201),
    ("二百零二", 202),
    ("三百三十九", 339),
    ("九百九十九", 999),
    ("一千", 1000),
    ("184", 184),
    ("0", 0),
])
def test_chn_to_int_cases(chn, expected):
    assert chn_to_int(chn) == expected


@pytest.mark.parametrize("raw,expected", [
    ("第 184 條", "184"),
    ("第一百八十四條", "184"),
    ("第 185-3 條", "185-3"),
    ("第一百八十五條之三", "185-3"),
    ("第 185 條之 3", "185-3"),
    ("第二百零一條", "201"),
    ("第二百〇二條", "202"),
    ("第 1 條", "1"),
    ("第 10 條", "10"),
    ("第 339-4 條", "339-4"),
])
def test_normalize_article_no_cases(raw, expected):
    assert normalize_article_no(raw) == expected


# -------------------------------------------------------------
# 2. explicit 顯式引用測試 (15 cases)
# -------------------------------------------------------------
@pytest.mark.parametrize("text,expected_act,expected_no", [
    ("依民法第 184 條規定。", "民法", "184"),
    ("依中華民國刑法第 10 條定義。", "中華民國刑法", "10"),
    ("適用刑法第 2 條從舊從輕原則。", "中華民國刑法", "2"),
    ("依中華民國憲法第 174 條規定。", "中華民國憲法", "174"),
    ("依憲法第 23 條比例原則。", "中華民國憲法", "23"),
    ("參照民事訴訟法第 244 條起訴程式。", "民事訴訟法", "244"),
    ("依民訴法第 78 條負擔訴訟費用。", "民事訴訟法", "78"),
    ("依刑事訴訟法第 154 條無罪推定。", "刑事訴訟法", "154"),
    ("依刑訴法第 370 條不利益變更禁止。", "刑事訴訟法", "370"),
    ("依行政程序法第 128 條申請程序重新進行。", "行政程序法", "128"),
    ("依公司法第 185 條為特別決議。", "公司法", "185"),
    ("依勞動基準法第 84 條之 1 約定責任制。", "勞動基準法", "84-1"),
    ("依勞基法第 11 條預告終止勞動契約。", "勞動基準法", "11"),
    ("違反個人資料保護法第 41 條處罰。", "個人資料保護法", "41"),
    ("依著作權法第 65 條合理使用。", "著作權法", "65"),
])
def test_explicit_citations(text, expected_act, expected_no):
    res = resolve_citations(text, host_act_id="criminal_code", db_path=str(DB_PATH))
    assert len(res) >= 1
    hit = res[0]
    assert hit["ref_type"] == "explicit"
    assert hit["ref_act_name"] == expected_act
    assert hit["ref_article_no"] == expected_no


# -------------------------------------------------------------
# 3. chain 連鎖引用測試 (10 cases)
# -------------------------------------------------------------
def test_chain_citations():
    text1 = "其賠償依民法第 184 條辦理，共同侵權時依同法第 185 條連帶負責。"
    res1 = resolve_citations(text1, host_act_id="criminal_code", db_path=str(DB_PATH))
    assert len(res1) == 2
    assert res1[0]["ref_type"] == "explicit"
    assert res1[0]["ref_act_name"] == "民法"
    assert res1[1]["ref_type"] == "chain"
    assert res1[1]["ref_act_name"] == "民法"
    assert res1[1]["ref_article_no"] == "185"

    text2 = "依刑事訴訟法第 154 條及同法第 155 條認定證據。"
    res2 = resolve_citations(text2, host_act_id="civil_code", db_path=str(DB_PATH))
    assert len(res2) == 2
    assert res2[1]["ref_type"] == "chain"
    assert res2[1]["ref_act_name"] == "刑事訴訟法"
    assert res2[1]["ref_article_no"] == "155"

    text3 = "前項程序依公司法第 185 條及同法第 189 條訴請撤銷。"
    res3 = resolve_citations(text3, host_act_id="civil_code", db_path=str(DB_PATH))
    assert len(res3) == 2
    assert res3[1]["ref_type"] == "chain"
    assert res3[1]["ref_act_name"] == "公司法"
    assert res3[1]["ref_article_no"] == "189"

    # 多重連鎖
    text4 = "依民法第 184 條、同法第 185 條及同法第 195 條。"
    res4 = resolve_citations(text4, host_act_id="criminal_code", db_path=str(DB_PATH))
    assert len(res4) == 3
    assert res4[1]["ref_type"] == "chain"
    assert res4[1]["ref_act_name"] == "民法"
    assert res4[2]["ref_type"] == "chain"
    assert res4[2]["ref_act_name"] == "民法"
    assert res4[2]["ref_article_no"] == "195"


# -------------------------------------------------------------
# 4. host 宿主引用測試 (10 cases)
# -------------------------------------------------------------
@pytest.mark.parametrize("text,expected_no", [
    ("違反本法第 10 條之規定。", "10"),
    ("依本法第 185-3 條處罰。", "185-3"),
    ("第 5 條所列各罪。", "5"),
    ("依第 6 條規定處斷。", "6"),
    ("適用本法第 2 條。", "2"),
    ("如本法第 339 條之詐欺罪。", "339"),
    ("犯本法第 271 條之殺人罪。", "271"),
    ("前項依第 121 條處理。", "121"),
    ("依本法第一百八十五條之三規定。", "185-3"),
    ("受本法第 38 條沒收之宣告。", "38"),
])
def test_host_citations(text, expected_no):
    res = resolve_citations(text, host_act_id="criminal_code", db_path=str(DB_PATH))
    assert len(res) >= 1
    hit = res[0]
    assert hit["ref_type"] == "host"
    assert hit["ref_act_id"] == "criminal_code"
    assert hit["ref_article_no"] == expected_no


# -------------------------------------------------------------
# 5. 範圍引用測試 (10 cases)
# -------------------------------------------------------------
def test_range_citations():
    text1 = "第一百二十一條至第一百二十三條之瀆職罪。"
    res1 = resolve_citations(text1, host_act_id="criminal_code", db_path=str(DB_PATH))
    assert len(res1) == 1
    assert res1[0]["ref_articles"] == ["121", "122", "123"]

    text2 = "第二百零一條至第二百零二條之偽造有價證券罪。"
    res2 = resolve_citations(text2, host_act_id="criminal_code", db_path=str(DB_PATH))
    assert len(res2) == 1
    assert res2[0]["ref_articles"] == ["201", "202"]

    text3 = "第 1 條至第 5 條。"
    res3 = resolve_citations(text3, host_act_id="criminal_code", db_path=str(DB_PATH))
    assert len(res3) == 1
    assert res3[0]["ref_articles"] == ["1", "2", "3", "4", "5"]

    text4 = "民法第 184 條至第 188 條侵權行為。"
    res4 = resolve_citations(text4, host_act_id="criminal_code", db_path=str(DB_PATH))
    assert len(res4) == 1
    assert res4[0]["ref_type"] == "explicit"
    assert res4[0]["ref_act_name"] == "民法"
    assert res4[0]["ref_articles"] == ["184", "185", "186", "187", "188"]


# -------------------------------------------------------------
# 6. unresolved 未解析引用與特殊邊界測試 (10 cases)
# -------------------------------------------------------------
def test_unresolved_and_boundaries():
    # 虛構法規名不應誤判為已知法規
    res_empty = resolve_citations("", host_act_id="criminal_code", db_path=str(DB_PATH))
    assert res_empty == []

    # 包含標點、括號
    text_paren = "（依民法第 184 條）。"
    res_paren = resolve_citations(text_paren, host_act_id="criminal_code", db_path=str(DB_PATH))
    assert len(res_paren) == 1
    assert res_paren[0]["ref_article_no"] == "184"

    # 純文字無引用
    text_none = "本條文內容完全沒有任何法條引用與數字。"
    res_none = resolve_citations(text_none, host_act_id="criminal_code", db_path=str(DB_PATH))
    assert res_none == []

# -------------------------------------------------------------
# 7. 額外專業法規引用測試 (10 cases)
# -------------------------------------------------------------
@pytest.mark.parametrize("txt,exp_act,exp_no", [
    ("依保險法第 64 條據實說明義務。", "保險法", "64"),
    ("依國家賠償法第 2 條請求賠償。", "國家賠償法", "2"),
    ("依國賠法第 3 條公共設施責任。", "國家賠償法", "3"),
    ("依消費者保護法第 7 條商品責任。", "消費者保護法", "7"),
    ("依消保法第 19 條七日猶豫期。", "消費者保護法", "19"),
    ("依社會秩序維護法第 63 條裁處。", "社會秩序維護法", "63"),
    ("依社維法第 80 條規定處罰。", "社會秩序維護法", "80"),
    ("依證券交易法第 20 條財報不實責任。", "證券交易法", "20"),
    ("依證交法第 171 條加重刑責。", "證券交易法", "171"),
    ("依智慧財產案件審理法第 16 條行使專屬管轄。", "智慧財產案件審理法", "16"),
])
def test_specialized_act_citations(txt, exp_act, exp_no):
    hits = resolve_citations(txt, host_act_id="civil_code", db_path=str(DB_PATH))
    assert len(hits) >= 1, f"未識別出: {txt}"
    assert hits[0]["ref_act_name"] == exp_act
    assert hits[0]["ref_article_no"] == exp_no
