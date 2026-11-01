"""
backend/lawplayer/parser.py

Pure parsing functions for LawPlayer HTML pages.
Takes raw HTML content (or responses) and returns a clean dictionary.
Never fills mock or synthetic data. Unparsed fields remain empty or empty lists.
"""

import re
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup


def parse_article_page(raw_html: str, source_url: str = "") -> Dict[str, Any]:
    """
    Parses a single LawPlayer article page HTML.
    
    Returns:
        dict with fields:
            - title: str
            - summary: str
            - vernacular_qa: List[Dict[str, str]]  # [{'q': ..., 'a': ...}]
            - deep_reading: str
            - interpretations: List[Dict[str, str]] # [{'org': ..., 'ref': ..., 'date': ..., 'url': ...}]
            - judgments: List[Dict[str, str]]      # [{'court': ..., 'ref': ..., 'url': ...}]
            - revisions: List[Dict[str, Any]]      # [{'date': ..., 'type': ..., 'reason': ...}]
            - source_url: str
    """
    soup = BeautifulSoup(raw_html, "html.parser")
    
    # 1. Title (條標)
    title = ""
    sum_span = soup.find("span", class_="artw-title-sum")
    if sum_span:
        title = sum_span.get_text(strip=True).strip("（）()")
    else:
        # Fallback to <title> tag extraction: e.g. "民法第 2 條（適用習慣之限制）- 2026..."
        title_tag = soup.find("title")
        if title_tag:
            m = re.search(r"[（(](.*?)[）)]", title_tag.get_text(strip=True))
            if m:
                title = m.group(1).strip()

    # 2. Key Summary (重點摘要)
    summary = ""
    lead = soup.find("p", class_="artw-lead")
    if lead:
        # Clone or strip child tags like 'artw-lead-tag'
        lead_clone = BeautifulSoup(str(lead), "html.parser")
        for tag in lead_clone.find_all("span", class_="artw-lead-tag"):
            tag.decompose()
        summary = lead_clone.get_text(strip=True)

    # 3. Vernacular Q&A (白話解說問答)
    vernacular_qa: List[Dict[str, str]] = []
    qa_blocks = soup.find_all("div", class_="artw-qa")
    for qa in qa_blocks:
        q_p = qa.find("p", class_="artw-qa-q")
        a_ps = qa.find_all("p", class_="artw-qa-a")
        q_text = q_p.get_text(strip=True) if q_p else ""
        if q_text.startswith("Q · "):
            q_text = q_text[4:].strip()
        elif q_text.startswith("Q ·"):
            q_text = q_text[3:].strip()
            
        a_text = "\n".join([a.get_text(strip=True) for a in a_ps if a.get_text(strip=True)])
        if q_text or a_text:
            vernacular_qa.append({"q": q_text, "a": a_text})

    # 4. Deep reading (深度閱讀)
    deep_reading = ""
    deep_sec = soup.find("section", id="w-deep")
    if deep_sec:
        paragraphs = [p.get_text(strip=True) for p in deep_sec.find_all("p") if p.get_text(strip=True)]
        deep_reading = "\n\n".join(paragraphs)

    # 5. Interpretations (相關函釋)
    interpretations: List[Dict[str, str]] = []
    interp_sec = soup.find("section", id="w-interp")
    if interp_sec:
        for li in interp_sec.find_all("li", class_="artw-interp-row"):
            a_el = li.find("a", class_="artw-interp-title")
            meta_el = li.find("span", class_="artw-interp-meta")
            ref = a_el.get_text(strip=True) if a_el else ""
            url = a_el.get("href", "") if a_el else ""
            if url and url.startswith("/"):
                url = f"https://lawplayer.com{url}"
                
            org = ""
            date = ""
            if meta_el:
                meta_spans = meta_el.find_all("span")
                if len(meta_spans) >= 1:
                    org = meta_spans[0].get_text(strip=True)
                if len(meta_spans) >= 2:
                    date = meta_spans[1].get_text(strip=True)
            
            interpretations.append({
                "org": org,
                "ref": ref,
                "date": date,
                "url": url
            })

    # 6. Judgments (裁判書 / 判例)
    judgments: List[Dict[str, str]] = []
    prec_sec = soup.find("section", id="w-precedents") or soup.find("section", id="w-judgments")
    if prec_sec:
        for a_el in prec_sec.find_all("a"):
            href = a_el.get("href", "")
            if href.startswith("/"):
                href = f"https://lawplayer.com{href}"
            full_txt = a_el.get_text(" ", strip=True)
            
            # Only extract court if explicitly present in link or meta text, otherwise leave empty
            court = ""
            for possible_court in ["最高法院", "高等法院", "地方法院", "行政法院", "智慧財產法院", "憲法法庭"]:
                if possible_court in full_txt:
                    court = possible_court
                    break
                
            judgments.append({
                "court": court,
                "ref": full_txt,
                "url": href
            })

    # 7. Revisions / Legislative history (立法沿革)
    revisions: List[Dict[str, Any]] = []
    evo_sec = soup.find("section", id="w-evolution")
    if evo_sec:
        # Check for structured revision entries
        rows = evo_sec.find_all("div", class_=re.compile(r"artw-evo|evolution-row"))
        for r in rows:
            revisions.append({
                "date": "",
                "type": "",
                "reason": r.get_text(strip=True)
            })

    # 8. Fact summaries for revisions if evo_sec has no direct rows
    if not revisions:
        facts = soup.find("section", class_="lartf-facts")
        if facts:
            fact_evo = facts.find("li", id="fact-evolution")
            if fact_evo:
                txt = fact_evo.get_text(strip=True)
                revisions.append({
                    "date": "",
                    "type": "沿革概況",
                    "reason": txt
                })

    return {
        "title": title,
        "summary": summary,
        "vernacular_qa": vernacular_qa,
        "deep_reading": deep_reading,
        "interpretations": interpretations,
        "judgments": judgments,
        "revisions": revisions,
        "source_url": source_url
    }


def parse_act_page(raw_html: str, source_url: str = "") -> Dict[str, Dict[str, str]]:
    """
    Parses a LawPlayer act page (e.g. /act/6437d054e800e5f0b93015aa).
    Extracts article links and titles.
    
    Returns:
        dict mapping normalized article_no (e.g. "1", "244", "31-1") to:
        {
            "id": str,
            "url": str,
            "title": str
        }
    """
    soup = BeautifulSoup(raw_html, "html.parser")
    links = soup.find_all("a", href=re.compile(r"^/article/[a-f0-9]+"))
    
    articles: Dict[str, Dict[str, str]] = {}
    for a in links:
        href = a.get("href", "")
        txt = a.get_text(" ", strip=True)
        # Match "第 1 條" or "第 31-1 條" or "第 31之1 條"
        m = re.search(r"第\s*(\d+(?:[-－之]\d+)?)\s*條(?:\s*(.*))?", txt)
        if m:
            raw_no = m.group(1).replace("－", "-").replace("之", "-")
            sub_title = m.group(2).strip() if m.group(2) else ""
            if raw_no not in articles:
                articles[raw_no] = {
                    "id": href.split("/")[-1],
                    "url": f"https://lawplayer.com{href}" if href.startswith("/") else href,
                    "title": sub_title
                }
    return articles

