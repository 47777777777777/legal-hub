import urllib.request
import re
import json
import time
from concurrent.futures import ThreadPoolExecutor

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) LegalHub/1.0"}

def fetch_article(art_no, art_id, sub_title):
    url = f"https://lawplayer.com/article/{art_id}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read().decode("utf-8")
        
        # Summary
        summary_m = re.search(r'class="artw-lead">(?:<span[^>]*>[^<]*</span>)?(.*?)</p>', html, re.DOTALL)
        summary = re.sub(r'<[^>]+>', '', summary_m.group(1)).strip() if summary_m else ""

        # QA
        qa_items = []
        qa_blocks = re.findall(r'<div class="artw-qa">(.*?)</div>', html, re.DOTALL)
        for block in qa_blocks:
            qs = re.findall(r'class="artw-qa-q">(.*?)</p>', block, re.DOTALL)
            ans = re.findall(r'class="artw-qa-a">(.*?)</p>', block, re.DOTALL)
            for q in qs:
                clean_q = re.sub(r'<[^>]+>', '', q).replace("Q", "").replace("‧", "").replace("<!-- -->", "").strip()
                clean_ans = "\n\n".join([re.sub(r'<[^>]+>', '', a).strip() for a in ans if a.strip()])
                if clean_q:
                    qa_items.append({"question": clean_q, "answer": clean_ans})

        # Deep reading
        deep_m = re.search(r'id="w-deep".*?class="artw-lead">(.*?)</p>', html, re.DOTALL)
        deep_reading = re.sub(r'<[^>]+>', '', deep_m.group(1)).strip() if deep_m else ""

        # Judgments
        judgments = []
        cross_m = re.search(r'id="w-cross"(.*?)</section>', html, re.DOTALL)
        if cross_m:
            j_links = re.findall(r'href="/judgment/[^"]*"[^>]*>(.*?)</a>', cross_m.group(1))
            for j in j_links:
                clean_j = re.sub(r'<[^>]+>', '', j).strip()
                if clean_j:
                    judgments.append({"court": "最高法院", "ref": clean_j, "summary": "實務裁判"})

        # Interps (函釋)
        interps = []
        interp_m = re.search(r'id="w-interp"(.*?)</section>', html, re.DOTALL)
        if interp_m:
            r_links = re.findall(r'href="/rule/[^"]*"[^>]*>(.*?)</a>', interp_m.group(1))
            for r in r_links:
                clean_r = re.sub(r'<[^>]+>', '', r).strip()
                if clean_r:
                    interps.append({"org": "主管機關函釋", "ref": clean_r})

        return {
            "article_no": art_no,
            "title": sub_title,
            "summary": summary,
            "vernacular_qa": qa_items,
            "deep_reading": deep_reading,
            "practical_insights": judgments,
            "administrative_rules": interps,
            "lawplayer_id": art_id
        }
    except Exception as e:
        print(f"Error fetching art {art_no}: {e}")
        return None

# Test fetching articles 5, 6, 7, 8, 9
test_batch = [
    ("5", "6438e7fbe800e5f0b932c85b", "保護原則、世界原則－國外犯罪之適用"),
    ("6", "6438e7fde800e5f0b932c87f", "公務員國外犯罪之適用"),
    ("7", "6438e7fee800e5f0b932c8a0", "屬人原則（二）－國民國外犯罪之適用"),
    ("8", "6438e800e800e5f0b932c8c7", "國外對國人犯罪之適用"),
    ("9", "6438e802e800e5f0b932c8ea", "外國裁判服刑之效力")
]

start = time.time()
with ThreadPoolExecutor(max_workers=5) as executor:
    results = list(executor.map(lambda args: fetch_article(*args), test_batch))

print(f"Fetched {len(results)} articles in {time.time() - start:.2f} seconds!")
for r in results:
    if r:
        print(f"Art {r['article_no']} ({r['title']}): Summary={r['summary'][:40]}... QA count={len(r['vernacular_qa'])}")

