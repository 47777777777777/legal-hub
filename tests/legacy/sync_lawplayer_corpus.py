"""
Synchronize complete rich legal enrichments from LawPlayer for Taiwan Criminal Code (422 articles).
Captures: Sub-titles, Plain Q&A, Deep Reading, Judgments, Administrative Rules, and Summaries.
"""
import os
import sys
import re
import json
import time
import urllib.request
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.db import get_connection, DB_FILE

ACT_URL = "https://lawplayer.com/act/6437d05ae800e5f0b9301656"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) LegalHub/1.0"}

def clean_text(s: str) -> str:
    s = re.sub(r'<[^>]+>', '', s)
    return " ".join(s.split()).strip()

def get_all_article_links():
    print("Fetching Criminal Code article list from LawPlayer...")
    req = urllib.request.Request(ACT_URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        html = resp.read().decode("utf-8")

    pattern = r'href="/article/([a-f0-9]+)"><b>第\s*([^<]+)\s*條</b>([^<]*)</a>'
    matches = re.findall(pattern, html)
    print(f"Found {len(matches)} articles in Criminal Code.")
    return [(m[1].strip().replace("之", "-").replace(" ", ""), m[0], m[2].strip()) for m in matches]

def fetch_single_article(art_no, art_id, sub_title):
    url = f"https://lawplayer.com/article/{art_id}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8")

        # 1. Title
        title = sub_title
        if not title:
            t_match = re.search(r'<title>.*?第\s*\d+\s*條(?:[｜「](.*?)[」｜])?.*?法律人', html)
            if t_match and t_match.group(1):
                title = t_match.group(1).strip()

        # 2. Summary
        summary_m = re.search(r'class="artw-lead">(?:<span[^>]*>[^<]*</span>)?(.*?)</p>', html, re.DOTALL)
        summary = clean_text(summary_m.group(1)) if summary_m else ""

        # 3. QA
        qa_items = []
        qa_blocks = re.findall(r'<div class="artw-qa">(.*?)</div>', html, re.DOTALL)
        for block in qa_blocks:
            qs = re.findall(r'class="artw-qa-q">(.*?)</p>', block, re.DOTALL)
            ans = re.findall(r'class="artw-qa-a">(.*?)</p>', block, re.DOTALL)
            for q in qs:
                clean_q = clean_text(q).replace("Q", "").replace("‧", "").replace("<!-- -->", "").strip()
                clean_ans = "\n\n".join([clean_text(a) for a in ans if clean_text(a)])
                if clean_q:
                    qa_items.append({"question": clean_q, "answer": clean_ans})

        # 4. Deep reading
        deep_m = re.search(r'id="w-deep".*?class="artw-lead">(.*?)</p>', html, re.DOTALL)
        deep_reading = clean_text(deep_m.group(1)) if deep_m else ""

        # 5. Judgments
        judgments = []
        cross_m = re.search(r'id="w-cross"(.*?)</section>', html, re.DOTALL)
        if cross_m:
            j_links = re.findall(r'href="/judgment/[^"]*"[^>]*>(.*?)</a>', cross_m.group(1))
            for j in j_links:
                cj = clean_text(j)
                if cj:
                    judgments.append({"court": "最高法院", "ref": cj, "summary": f"法律人精選最高法院實務裁判（案號：{cj}）"})

        # 6. Interps (行政函釋)
        interps = []
        interp_m = re.search(r'id="w-interp"(.*?)</section>', html, re.DOTALL)
        if interp_m:
            r_links = re.findall(r'href="/rule/[^"]*"[^>]*>(.*?)</a>', interp_m.group(1))
            for r in r_links:
                cr = clean_text(r)
                if cr:
                    interps.append({"org": "法務部", "ref": cr, "summary": f"法務部行政解釋函令（字號：{cr}）"})

        # 7. Legislative reasons
        reasons = []
        rev_m = re.search(r'id="w-rev"(.*?)</section>', html, re.DOTALL)
        if rev_m:
            dates = re.findall(r'class="artw-rev-date"[^>]*>(.*?)<', rev_m.group(1))
            bodies = re.findall(r'class="artw-rev-body"[^>]*>(.*?)</div>', rev_m.group(1), re.DOTALL)
            for d, b in zip(dates, bodies):
                reasons.append({"date": d.strip(), "reason": clean_text(b)})

        return {
            "article_no": art_no,
            "title": title,
            "summary": summary,
            "vernacular_qa": qa_items,
            "deep_reading": deep_reading,
            "practical_insights": judgments,
            "administrative_rules": interps,
            "amendment_history": reasons,
            "lawplayer_link": f"https://lawplayer.com/article/{art_id}"
        }
    except Exception as e:
        print(f"Error on art {art_no}: {e}")
        return None

def main():
    output_cache = os.path.join(BASE_DIR, "data", "lawplayer_criminal_code_enrichments.json")
    results = {}
    if os.path.exists(output_cache):
        print(f"Loading existing cache from {output_cache}...")
        with open(output_cache, "r", encoding="utf-8") as f:
            results = json.load(f)
        print(f"Loaded {len(results)} articles from cache.")

    if not results:
        links = get_all_article_links()
        if not links:
            print("No articles found to sync.")
            return

        print(f"Starting concurrent scraping of {len(links)} articles with 8 workers...")
        completed = 0

        with ThreadPoolExecutor(max_workers=8) as executor:
            future_map = {executor.submit(fetch_single_article, *item): item[0] for item in links}
            for future in as_completed(future_map):
                art_no = future_map[future]
                try:
                    res = future.result()
                    if res:
                        results[art_no] = res
                except Exception as e:
                    print(f"Failed {art_no}: {e}")
                completed += 1
                if completed % 25 == 0 or completed == len(links):
                    print(f"Progress: {completed}/{len(links)} articles processed ({len(results)} successful)...")

        print(f"Scraping completed! Successfully extracted {len(results)} enriched articles.")

        # Save to local cache JSON
        with open(output_cache, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"Cached enrichments to {output_cache}")

    # Write into SQLite
    conn = get_connection(DB_FILE)
    cur = conn.cursor()

    updated_count = 0
    for art_no, data in results.items():
        title = data.get("title", "")
        # Update title in articles table if present
        if title:
            cur.execute("UPDATE articles SET title = ? WHERE act_id = 'criminal_code' AND article_no = ?", (title, art_no))

        cur.execute("""
            INSERT INTO article_enrichments (
                act_id, article_no, summary, vernacular_qa_json,
                practical_insights_json, amendment_history_json,
                official_letters_json, legal_definition
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(act_id, article_no) DO UPDATE SET
                summary = excluded.summary,
                vernacular_qa_json = excluded.vernacular_qa_json,
                practical_insights_json = CASE WHEN excluded.practical_insights_json != '[]' THEN excluded.practical_insights_json ELSE article_enrichments.practical_insights_json END,
                amendment_history_json = CASE WHEN excluded.amendment_history_json != '[]' THEN excluded.amendment_history_json ELSE article_enrichments.amendment_history_json END,
                official_letters_json = CASE WHEN excluded.official_letters_json != '[]' THEN excluded.official_letters_json ELSE article_enrichments.official_letters_json END,
                legal_definition = CASE WHEN excluded.legal_definition != '' THEN excluded.legal_definition ELSE article_enrichments.legal_definition END
        """, (
            "criminal_code",
            art_no,
            data.get("summary", ""),
            json.dumps(data.get("vernacular_qa", []), ensure_ascii=False),
            json.dumps(data.get("practical_insights", []), ensure_ascii=False),
            json.dumps(data.get("amendment_history", []), ensure_ascii=False),
            json.dumps(data.get("administrative_rules", []), ensure_ascii=False),
            data.get("deep_reading", "")
        ))
        updated_count += 1

    # Mark act as enriched
    cur.execute("UPDATE acts SET is_enriched = 1 WHERE id = 'criminal_code'")
    conn.commit()
    conn.close()
    print(f"Successfully updated SQLite database with {updated_count} enriched articles for Criminal Code!")

if __name__ == "__main__":
    main()
