import os
import sys
import json
import re
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHLAW_PATH = os.path.join(BASE_DIR, "data", "ChLaw.json")

def test_abolished_act_ui():
    # Load expected data from ChLaw.json
    with open(CHLAW_PATH, "r", encoding="utf-8-sig") as f:
        chlaw = json.load(f)
    
    act_data = next(x for x in chlaw["Laws"] if "動員戡亂時期臨時條款" in x["LawName"])
    expected_name = act_data["LawName"]
    expected_category = act_data["LawCategory"]
    expected_intro = act_data["LawForeword"].strip()
    expected_abandon_date_str = "民國 80 年 05 月 01 日"
    art1_data = next(x for x in act_data["LawArticles"] if x.get("ArticleNo") in ("1", "第 1 條", "1."))
    expected_art1_content = art1_data["ArticleContent"].strip()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        
        # Open abolished act permalink
        page.goto("http://127.0.0.1:8080/#/act/a0000005/article/1", wait_until="networkidle")
        
        # 1. Page opens normally and displays act name in tab
        page.wait_for_selector(".research-tab-item.active", timeout=10000)
        tab_text = page.locator(".research-tab-item.active").text_content()
        assert expected_name in tab_text, f"Expected {expected_name} in {tab_text}"

        # 2. Displays official '廢止日期：民國 80 年 05 月 01 日' and '法規類別：廢止法規'
        page.wait_for_selector("#act-meta-inline", timeout=10000)
        meta_inline = page.locator("#act-meta-inline").text_content()
        assert "廢止日期" in meta_inline, f"Expected '廢止日期' in {meta_inline}"
        assert expected_abandon_date_str in meta_inline, f"Expected '{expected_abandon_date_str}' in {meta_inline}"
        assert "法規類別" in meta_inline, f"Expected '法規類別' in {meta_inline}"
        assert "廢止法規" in meta_inline, f"Expected '廢止法規' in {meta_inline}"

        # 3. Must NOT contain synthesized '總統令廢止' or '【已廢止：廢】' or '於...廢止'
        assert "總統令廢止" not in meta_inline, "Must not contain synthesized '總統令廢止'"
        assert "已廢止：廢" not in meta_inline, "Must not contain raw '已廢止：廢'"
        assert "於" not in meta_inline or "廢止" not in meta_inline.split("於")[-1][:10], "Must not contain synthesized '於...廢止'"

        # 4. Opening enacting formula is rendered as introductory text WITHOUT synthesized '【前言】' badge
        page.wait_for_selector("#act-foreword-card", timeout=10000)
        foreword_card_text = page.locator("#act-foreword-card").text_content()
        assert "【前言】" not in foreword_card_text, "A0000005 enacting text must NOT be falsely badged as '【前言】'"
        clean_intro_expected = re.sub(r"\s+", "", expected_intro)
        clean_intro_rendered = re.sub(r"\s+", "", foreword_card_text)
        assert clean_intro_expected in clean_intro_rendered, "Official opening text content missing from UI"

        # 5. Article 1 does NOT contain synthesized '第 1 條' header
        card1_no_text = page.locator("#article-card-1 .article-card-no").text_content()
        assert "第 1 條" not in card1_no_text, f"Unexpected '第 1 條' synthesized in card header: {card1_no_text}"

        # 6. Article 1 content is readable and matches ChLaw.json verbatim
        page.wait_for_selector("#article-card-1", timeout=10000)
        page.locator("#article-card-1").click()
        page.wait_for_selector(".drawer-hero-article-box .para-body", timeout=10000)
        paras = page.locator(".drawer-hero-article-box .para-body").all_text_contents()
        drawer_para_text = "".join(paras)
        
        clean_expected = re.sub(r"\s+", "", expected_art1_content)
        clean_para = re.sub(r"\s+", "", drawer_para_text)
        assert clean_expected in clean_para, f"Expected full article content {clean_expected[:50]}... in drawer"

        # 7. Check Constitution (A0000001): unbadged plain text (Prompt 4F)
        page.goto("http://127.0.0.1:8080/#/act/constitution/article/1", wait_until="networkidle")
        page.wait_for_function("() => window.legalHubApp && window.legalHubApp.currentActId === 'constitution'", timeout=10000)
        page.wait_for_selector("#act-foreword-card", timeout=10000)
        const_foreword_text = page.locator("#act-foreword-card").text_content()
        assert "【前言】" not in const_foreword_text, "Prompt 4F: All forewords must be unbadged plain text"
        assert "受全體國民之付託" in const_foreword_text, "Constitution preamble text missing from card"

        browser.close()
