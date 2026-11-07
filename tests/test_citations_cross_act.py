"""
tests/test_citations_cross_act.py

Prompt 4G Section 1.3:
先寫並貼出會重現「引用懸停指到錯誤法規」的測試（在尚未實作 backend/citations.py 之前必須失敗）：
Fixture 中一部「刑法」條文內含「民法第 184 條」，斷言引用目標是民法第 184 條而不是刑法第 184 條。
實作後該測試必須通過。
"""

import pytest
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data" / "legal_hub.db"

def test_cross_act_citation_resolution():
    """
    重現並防止「刑法條文中的『民法第 184 條』被指到刑法第 184 條」的缺陷。
    """
    from backend.citations import resolve_citations
    
    # 模擬刑法條文內文，包含跨法規顯式引用 (explicit)、同法接續引用 (chain)、本法引用 (host)
    fixture_text = "行為人違反本法第 10 條之規定者，處有期徒刑。其民事賠償責任，依民法第 184 條及同法第 185 條規定辦理。"
    host_act_id = "criminal_code"
    
    citations = resolve_citations(fixture_text, host_act_id=host_act_id, db_path=str(DB_PATH))
    
    # 查找「民法第 184 條」的解析結果
    ref_184 = next((c for c in citations if "184" in c["ref_article_no"]), None)
    assert ref_184 is not None, "必須識別出『民法第 184 條』引用"
    
    # 關鍵斷言：目標法規必須是民法 (civil_code 或 B0000001)，絕對不得指到當前宿主法規 (criminal_code)！
    assert ref_184["ref_act_name"] == "民法"
    assert ref_184["ref_act_id"] in ("civil_code", "b0000001", "B0000001")
    assert ref_184["ref_article_no"] == "184"
    assert ref_184["ref_type"] == "explicit"
    assert ref_184["ref_act_id"] != "criminal_code", "錯誤：民法第 184 條不可指到刑法！"
    
    # 查找「同法第 185 條」的解析結果 (chain 規則)
    ref_185 = next((c for c in citations if "185" in c["ref_article_no"]), None)
    assert ref_185 is not None, "必須識別出『同法第 185 條』引用"
    assert ref_185["ref_act_name"] == "民法"
    assert ref_185["ref_act_id"] in ("civil_code", "b0000001", "B0000001")
    assert ref_185["ref_article_no"] == "185"
    assert ref_185["ref_type"] == "chain"
    
    # 查找「本法第 10 條」的解析結果 (host 規則)
    ref_10 = next((c for c in citations if "10" in c["ref_article_no"]), None)
    assert ref_10 is not None, "必須識別出『本法第 10 條』引用"
    assert ref_10["ref_act_id"] == "criminal_code"
    assert ref_10["ref_article_no"] == "10"
    assert ref_10["ref_type"] == "host"
