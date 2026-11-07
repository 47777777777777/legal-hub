import urllib.request
import re
import json

url = "https://lawplayer.com/article/6438e7fee800e5f0b932c8a0"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) LegalHub/1.0"})
with urllib.request.urlopen(req, timeout=10) as resp:
    html = resp.read().decode("utf-8")

# Parse with regex or BeautifulSoup
# 1. Title
title_m = re.search(r'<title>.*?第\s*\d+\s*條(?:[｜「](.*?)[」｜])?.*?法律人', html)
sub_title = title_m.group(1).strip() if title_m and title_m.group(1) else ""

# 2. Summary
summary_m = re.search(r'class="artw-lead">(?:<span[^>]*>[^<]*</span>)?(.*?)</p>', html, re.DOTALL)
summary = re.sub(r'<[^>]+>', '', summary_m.group(1)).strip() if summary_m else ""

# 3. QA
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

# 4. Deep reading (深度解讀)
deep_m = re.search(r'id="w-deep".*?class="artw-lead">(.*?)</p>', html, re.DOTALL)
deep_reading = re.sub(r'<[^>]+>', '', deep_m.group(1)).strip() if deep_m else ""

# 5. Judgments (裁判)
judgments = []
cross_m = re.search(r'id="w-cross"(.*?)</section>', html, re.DOTALL)
if cross_m:
    j_links = re.findall(r'href="/judgment/[^"]*"[^>]*>(.*?)</a>', cross_m.group(1))
    for j in j_links:
        clean_j = re.sub(r'<[^>]+>', '', j).strip()
        if clean_j:
            judgments.append({"court": "最高法院", "ref": clean_j, "summary": "法律人引用實務裁判見解"})

# 6. Interps (函釋)
interps = []
interp_m = re.search(r'id="w-interp"(.*?)</section>', html, re.DOTALL)
if interp_m:
    r_links = re.findall(r'href="/rule/[^"]*"[^>]*>(.*?)</a>', interp_m.group(1))
    for r in r_links:
        clean_r = re.sub(r'<[^>]+>', '', r).strip()
        if clean_r:
            interps.append({"org": "法務部", "ref": clean_r})

# 7. Legislative Reasons (立法沿革與理由)
reasons = []
rev_m = re.search(r'id="w-rev"(.*?)</section>', html, re.DOTALL)
if rev_m:
    dates = re.findall(r'class="artw-rev-date"[^>]*>(.*?)<', rev_m.group(1))
    bodies = re.findall(r'class="artw-rev-body"[^>]*>(.*?)</div>', rev_m.group(1), re.DOTALL)
    for d, b in zip(dates, bodies):
        clean_b = re.sub(r'<[^>]+>', '', b).strip()
        reasons.append({"date": d.strip(), "reason": clean_b})

result = {
    "sub_title": sub_title,
    "summary": summary,
    "qa_items": qa_items,
    "deep_reading": deep_reading,
    "judgments": judgments,
    "interps": interps,
    "reasons": reasons
}

with open("scripts/parsed_art_7.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("Parsed successfully!")
print(json.dumps(result, ensure_ascii=False, indent=2))
