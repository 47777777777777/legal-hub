import os
import re
import pytest
from backend.lis.parser import (
    cn_to_int,
    parse_lis_article_no,
    parse_full_act_reasons,
    parse_comparison_table,
    parse_single_article
)

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "lis", "samples")


def test_chinese_number_conversion():
    assert cn_to_int("一") == 1
    assert cn_to_int("十") == 10
    assert cn_to_int("十五") == 15
    assert cn_to_int("二十") == 20
    assert cn_to_int("二十四") == 24
    assert cn_to_int("一百") == 100
    assert cn_to_int("一百二十八") == 128
    assert cn_to_int("一百七十四") == 174
    assert cn_to_int("二百四十四") == 244
    assert cn_to_int("三百零五") == 305


def test_parse_lis_article_no():
    assert parse_lis_article_no("第一條") == "1"
    assert parse_lis_article_no("第二條") == "2"
    assert parse_lis_article_no("第一百二十八條") == "128"
    assert parse_lis_article_no("第一百七十四條之一") == "174-1"
    assert parse_lis_article_no("第一百七十四條 之一") == "174-1"
    assert parse_lis_article_no("第二百四十四條") == "244"


def test_parse_full_act_sample_1():
    path = os.path.join(SAMPLE_DIR, "sample_1.html")
    assert os.path.exists(path), f"Sample 1 not found at {path}"
    
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        raw_html = f.read()

    articles = parse_full_act_reasons(raw_html, raw_path=path, source_url="https://lis.ly.gov.tw/lglawc/lawsingle?sample1")
    assert len(articles) >= 170, f"Expected at least 170 articles, got {len(articles)}"

    # Check Article 1
    art1 = next((a for a in articles if a["article_no"] == "1"), None)
    assert art1 is not None, "Article 1 should be parsed from Sample 1"
    assert art1["version_date"] == "0880115"
    assert "為使行政行為遵循公正、公開與民主之程序" in art1["content"]
    assert "一、本條明定本法之立法目的。" in art1["reason"]
    assert "三、參考日本行政手續法第一條、韓國一九八七年行政程序法草案第一條。" in art1["reason"]

    # Verbatim substring test against clean raw text
    clean_raw_nospace = re.sub(r'\s+', '', re.sub(r'<[^>]+>', '', raw_html))
    assert re.sub(r'\s+', '', art1["reason"]) in clean_raw_nospace

    # Check Article 128 (880115 version)
    art128 = next((a for a in articles if a["article_no"] == "128"), None)
    assert art128 is not None, "Article 128 should be parsed from Sample 1"
    assert re.sub(r'\s+', '', art128["reason"]) in clean_raw_nospace

    # Check Article 174-1
    art174_1 = next((a for a in articles if a["article_no"] == "174-1"), None)
    assert art174_1 is not None, "Article 174-1 should be parsed from Sample 1"


def test_parse_comparison_table_sample_2():
    path = os.path.join(SAMPLE_DIR, "sample_2.html")
    assert os.path.exists(path), f"Sample 2 not found at {path}"

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        raw_html = f.read()

    res = parse_comparison_table(raw_html, raw_path=path, source_url="https://lis.ly.gov.tw/lglawc/lawsingle?sample2")
    assert res["law_name"] == "行政程序法"
    assert res["article_no"] == "128"
    assert res["action_type"] == "修正"
    assert res["new_version_date"] == "1091230"
    assert res["old_version_date"] == "1041211"
    
    assert "一、本項新增。" in res["reason"]
    assert "二、現行實務適用行政程序法第一百二十八條規定" in res["reason"]
    assert "確保人民權利之實現。" in res["reason"]

    # Verbatim substring test against clean raw text
    clean_raw_nospace = re.sub(r'\s+', '', re.sub(r'<[^>]+>', '', raw_html))
    assert re.sub(r'\s+', '', res["reason"]) in clean_raw_nospace
    assert re.sub(r'\s+', '', res["new_content"]) in clean_raw_nospace


def test_parse_single_article_sample_3():
    path = os.path.join(SAMPLE_DIR, "sample_3.html")
    assert os.path.exists(path), f"Sample 3 not found at {path}"

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        raw_html = f.read()

    res = parse_single_article(raw_html, raw_path=path, source_url="https://lis.ly.gov.tw/lglawc/lawsingle?sample3")
    assert res["law_name"] == "行政程序法"
    assert res["law_code"] == "01830"
    assert res["article_no"] == "128"
    assert res["action_type"] == "修正"
    assert "yellow_btn05" in res["comparison_url"] or "lawsingle" in res["comparison_url"]

    assert "一、本項新增。" in res["reason"]

    # Verbatim substring test against clean raw text
    clean_raw_nospace = re.sub(r'\s+', '', re.sub(r'<[^>]+>', '', raw_html))
    assert re.sub(r'\s+', '', res["reason"]) in clean_raw_nospace
