import os
import re
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
raw_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'raw', 'lawplayer', 'civil_procedure_code')

for name in ['civil_art_2.body.html', 'cpc_art_244.body.html']:
    with open(os.path.join(raw_dir, name), 'r', encoding='utf-8') as f:
        html = f.read()

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    
    print(f"\n======================== {name} ========================")
    
    # 1. Title
    h1 = soup.find('h1', class_='artw-title')
    sum_span = soup.find('span', class_='artw-title-sum')
    title = ""
    if sum_span:
        title = sum_span.get_text(strip=True).strip('（）()')
    print("Title:", repr(title))
    
    # 2. Summary
    lead = soup.find('p', class_='artw-lead')
    summary = ""
    if lead:
        # strip the tag span (e.g. 重點摘要)
        for tag in lead.find_all('span', class_='artw-lead-tag'):
            tag.decompose()
        summary = lead.get_text(strip=True)
    print("Summary:", repr(summary))
    
    # 3. Vernacular Q&A
    qa_blocks = soup.find_all('div', class_='artw-qa')
    vernacular_qa = []
    for qa in qa_blocks:
        q_p = qa.find('p', class_='artw-qa-q')
        a_ps = qa.find_all('p', class_='artw-qa-a')
        q_text = q_p.get_text(strip=True) if q_p else ""
        if q_text.startswith("Q · "):
            q_text = q_text[4:].strip()
        a_text = "\n".join([a.get_text(strip=True) for a in a_ps if a.get_text(strip=True)])
        if q_text or a_text:
            vernacular_qa.append({"q": q_text, "a": a_text})
    print(f"Vernacular QA ({len(vernacular_qa)}):", vernacular_qa)
    
    # 4. Deep reading
    deep_sec = soup.find('section', id='w-deep')
    deep_reading = ""
    if deep_sec:
        # get text from paragraphs inside deep section
        paragraphs = [p.get_text(strip=True) for p in deep_sec.find_all('p') if p.get_text(strip=True)]
        deep_reading = "\n\n".join(paragraphs)
    print("Deep reading:", repr(deep_reading[:150]))
    
    # 5. Interpretations
    interps = []
    interp_sec = soup.find('section', id='w-interp')
    if interp_sec:
        for li in interp_sec.find_all('li', class_='artw-interp-row'):
            a_el = li.find('a', class_='artw-interp-title')
            meta_el = li.find('span', class_='artw-interp-meta')
            ref = a_el.get_text(strip=True) if a_el else ""
            url = a_el.get('href', '') if a_el else ""
            org = ""
            date = ""
            if meta_el:
                meta_spans = meta_el.find_all('span')
                if len(meta_spans) >= 1:
                    org = meta_spans[0].get_text(strip=True)
                if len(meta_spans) >= 2:
                    date = meta_spans[1].get_text(strip=True)
            interps.append({
                "org": org,
                "ref": ref,
                "date": date,
                "url": f"https://lawplayer.com{url}" if url.startswith('/') else url
            })
    print(f"Interpretations ({len(interps)}):", interps)
    
    # 6. Judgments
    judgments = []
    prec_sec = soup.find('section', id='w-precedents')
    if prec_sec:
        for a_el in prec_sec.find_all('a'):
            href = a_el.get('href', '')
            full_txt = a_el.get_text(" ", strip=True)
            judgments.append({
                "court": "最高法院" if "渝上" in full_txt or "上字" in full_txt else "",
                "ref": full_txt,
                "url": f"https://lawplayer.com{href}" if href.startswith('/') else href
            })
    print(f"Judgments ({len(judgments)}):", judgments[:2])
    
    # 7. Revisions
    revisions = []
    evo_sec = soup.find('section', id='w-evolution')
    # Or from facts section
    facts = soup.find('section', class_='lartf-facts')
    fact_evo = facts.find('li', id='fact-evolution') if facts else None
    evo_summary = fact_evo.get_text(strip=True) if fact_evo else ""
    # Check if there are revision rows inside w-evolution
    if evo_sec:
        # inspect children
        rows = evo_sec.find_all('div', class_=re.compile(r'artw-evo|evolution'))
        for r in rows:
            revisions.append({"summary": r.get_text(strip=True)})
    print("Revisions summary:", repr(evo_summary), "revisions list:", revisions)

