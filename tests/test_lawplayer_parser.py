"""
tests/test_lawplayer_parser.py

Offline unit tests for backend.lawplayer.parser.
Uses fixed sample files in data/raw/lawplayer/civil_procedure_code/.
No network requests are made.
"""

import os
import pytest
from backend.lawplayer.parser import parse_article_page, parse_act_page

RAW_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "raw",
    "lawplayer",
    "civil_procedure_code"
)


@pytest.fixture
def civil_art_2_html():
    path = os.path.join(RAW_DIR, "civil_art_2.body.html")
    assert os.path.exists(path), f"Missing fixture file: {path}"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def cpc_art_244_html():
    path = os.path.join(RAW_DIR, "cpc_art_244.body.html")
    assert os.path.exists(path), f"Missing fixture file: {path}"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def cpc_act_html():
    path = os.path.join(RAW_DIR, "cpc_act.body.html")
    assert os.path.exists(path), f"Missing fixture file: {path}"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def test_civil_art_2_benchmark(civil_art_2_html):
    """
    Benchmark requirement from user prompt:
    - 標題: 「適用習慣之限制」
    - 相關函釋 5 則:
        1. 司法院 法律字第 10503501700 號 2016-01-30
        2. 司法院 法律字第 10403516610 號 2016-01-11
        3. 司法院 （83）法律字第 09061 號 1994-05-05
        4. 司法院 （70）法律字第 14146 號 1981-11-20
        5. 司法院 （63）台函民字第 05357 號 1974-06-23
    - 立法沿革: 1 版立法沿革
    """
    res = parse_article_page(civil_art_2_html, source_url="https://lawplayer.com/article/6438cdc1e800e5f0b9327944")

    # 1. Title
    assert res["title"] == "適用習慣之限制"

    # 2. Interpretations
    assert len(res["interpretations"]) == 5
    expected_interps = [
        ("司法院", "法律字第 10503501700 號", "2016-01-30"),
        ("司法院", "法律字第 10403516610 號", "2016-01-11"),
        ("司法院", "（83）法律字第 09061 號", "1994-05-05"),
        ("司法院", "（70）法律字第 14146 號", "1981-11-20"),
        ("司法院", "（63）台函民字第 05357 號", "1974-06-23")
    ]
    for actual, (exp_org, exp_ref, exp_date) in zip(res["interpretations"], expected_interps):
        assert actual["org"] == exp_org
        assert actual["ref"] == exp_ref
        assert actual["date"] == exp_date
        assert actual["url"].startswith("https://lawplayer.com/rule/")

    # 3. Legislative history / Revisions
    assert len(res["revisions"]) >= 1
    assert any("1 個版本" in rev["reason"] for rev in res["revisions"])

    # 4. Summary & QA
    assert "習慣" in res["summary"]
    assert len(res["vernacular_qa"]) >= 1
    assert "法律上有效嗎" in res["vernacular_qa"][0]["q"]


def test_cpc_art_244_parser(cpc_art_244_html):
    """
    Verify Civil Procedure Code Art 244:
    - 標題: 「起訴之程式」
    - 相關函釋 3 則 (發文機關為司法院，不是一律法務部)
    """
    res = parse_article_page(cpc_art_244_html, source_url="https://lawplayer.com/article/6438cf6fe800e5f0b9328b7a")
    assert res["title"] == "起訴之程式"
    assert len(res["interpretations"]) == 3
    for interp in res["interpretations"]:
        assert interp["org"] == "司法院"
        assert interp["ref"] != ""
        assert interp["date"] != ""
        assert interp["url"].startswith("https://lawplayer.com/rule/")


def test_parse_act_page_cpc(cpc_act_html):
    """
    Verify that act page parsing extracts all 800 articles matching MOJ.
    """
    articles = parse_act_page(cpc_act_html, source_url="https://lawplayer.com/act/6437d054e800e5f0b93015aa")
    assert len(articles) == 800
    assert "1" in articles
    assert articles["1"]["title"] == "普通審判籍－自然人"
    assert "244" in articles
    assert articles["244"]["title"] == "起訴之程式"
    assert "277" in articles
    assert articles["277"]["title"] == "舉證責任分配之原則"
    assert "31-1" in articles
    assert "77-1" in articles


def test_no_paywall_strings_in_parsed_results(civil_art_2_html, cpc_art_244_html):
    """
    Prompt 3 requirement:
    - Assert parsed results across civil art 2 and cpc art 244 have ZERO paywall strings
      ('在牆內', '在上方解鎖', '解鎖', '會員專屬', '加入會員') in any string field or list element.
    - Assert cpc art 244 parses paywalled_counts: {'legislative_reasons': 4} without marketing text.
    """
    from backend.lawplayer.parser import FORBIDDEN_PAYWALL_PATTERNS

    for html_fixture, name in [(civil_art_2_html, "civil_art_2"), (cpc_art_244_html, "cpc_art_244")]:
        res = parse_article_page(html_fixture)
        
        # Traverse every string in the result dict
        def check_val(val, path=""):
            if isinstance(val, str):
                for pat in FORBIDDEN_PAYWALL_PATTERNS:
                    assert pat not in val, f"Forbidden paywall pattern '{pat}' found in {name} at {path}: '{val}'"
            elif isinstance(val, dict):
                for k, v in val.items():
                    check_val(v, f"{path}.{k}")
            elif isinstance(val, list):
                for idx, item in enumerate(val):
                    check_val(item, f"{path}[{idx}]")

        check_val(res)

    # Check paywalled count extraction on CPC 244
    res_244 = parse_article_page(cpc_art_244_html)
    assert res_244.get("paywalled_counts") == {"legislative_reasons": 4}

