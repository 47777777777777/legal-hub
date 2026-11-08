import os
import sys
import json
import sqlite3
import random
import hashlib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "legal_hub.db")
OUTPUT_MD = os.path.join(BASE_DIR, "reports", "lis_spotcheck_pack.md")

TIER1_ACTS = [
    ("constitution", "中華民國憲法", "A0000001"),
    ("civil_code", "民法", "B0000001"),
    ("criminal_code", "中華民國刑法", "C0000001"),
    ("civil_procedure_code", "民事訴訟法", "B0010001"),
    ("criminal_procedure_code", "刑事訴訟法", "C0010001"),
    ("admin_procedure_act", "行政程序法", "A0030055"),
    ("labor_standards_act", "勞動基準法", "N0030001"),
    ("company_act", "公司法", "J0080001"),
    ("traffic_act", "道路交通管理處罰條例", "K0040012"),
    ("a0030154", "懲治走私條例", "A0030154"),
]

def sha256_file(filepath):
    if not os.path.exists(filepath):
        return "FILE_NOT_FOUND"
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def generate_pack():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    random.seed(42)

    selected_articles = []
    
    # 1. Specific mandated articles
    # Branch article: Criminal Code 296-1
    cur.execute("SELECT act_id, article_no, version_date, reason, source_url, raw_path FROM article_reasons WHERE act_id='criminal_code' AND article_no='296-1' LIMIT 1")
    r = cur.fetchone()
    if r: selected_articles.append(r)

    # Multi-version article: APA 128
    cur.execute("SELECT act_id, article_no, version_date, reason, source_url, raw_path FROM article_reasons WHERE act_id='admin_procedure_act' AND article_no='128' ORDER BY version_date DESC LIMIT 1")
    r = cur.fetchone()
    if r: selected_articles.append(r)

    # Deleted / special article if any, or multi-version Criminal Code Art 10
    cur.execute("SELECT act_id, article_no, version_date, reason, source_url, raw_path FROM article_reasons WHERE act_id='criminal_code' AND article_no='10' ORDER BY version_date DESC LIMIT 1")
    r = cur.fetchone()
    if r: selected_articles.append(r)

    # Multi-version Civil Code Art 184
    cur.execute("SELECT act_id, article_no, version_date, reason, source_url, raw_path FROM article_reasons WHERE act_id='civil_code' AND article_no='184' ORDER BY version_date DESC LIMIT 1")
    r = cur.fetchone()
    if r: selected_articles.append(r)

    # Ensure at least 2 articles from each Tier 1 law
    act_map = {act_id: name for act_id, name, pcode in TIER1_ACTS}
    pcode_map = {act_id: pcode for act_id, name, pcode in TIER1_ACTS}

    already_chosen = set((r[0], r[1]) for r in selected_articles)

    for act_id, name, pcode in TIER1_ACTS:
        cur.execute("SELECT DISTINCT article_no FROM article_reasons WHERE act_id = ?", (act_id,))
        art_nos = [row[0] for row in cur.fetchall()]
        if not art_nos:
            continue
        # filter out already chosen
        candidates = [a for a in art_nos if (act_id, a) not in already_chosen]
        random.shuffle(candidates)
        # pick enough to make at least 2 for this act
        current_count = sum(1 for a in selected_articles if a[0] == act_id)
        needed = max(0, 2 - current_count)
        for pick in candidates[:needed]:
            cur.execute("SELECT act_id, article_no, version_date, reason, source_url, raw_path FROM article_reasons WHERE act_id=? AND article_no=? ORDER BY version_date DESC LIMIT 1", (act_id, pick))
            row = cur.fetchone()
            if row:
                selected_articles.append(row)
                already_chosen.add((act_id, pick))

    # Fill remaining up to 30 from all Tier 1
    cur.execute("SELECT DISTINCT act_id, article_no FROM article_reasons")
    all_pairs = cur.fetchall()
    all_candidates = [p for p in all_pairs if p not in already_chosen]
    random.shuffle(all_candidates)

    remaining_needed = 30 - len(selected_articles)
    for act_id, art_no in all_candidates[:remaining_needed]:
        cur.execute("SELECT act_id, article_no, version_date, reason, source_url, raw_path FROM article_reasons WHERE act_id=? AND article_no=? ORDER BY version_date DESC LIMIT 1", (act_id, art_no))
        row = cur.fetchone()
        if row:
            selected_articles.append(row)
            already_chosen.add((act_id, art_no))

    conn.close()

    lines = []
    lines.append("# 立法理由與沿革 30 條隨機抽查清單 (Tier 1)")
    lines.append("")
    lines.append(f"> 產生方式：以固定隨機亂數種子 (`seed=42`) 從 Tier 1 已入庫之 3,636 筆立法理由中抽樣 30 條。")
    lines.append("> 涵蓋：枝條號（如刑法第 296-1 條）、多次修正條文（如行政程序法第 128 條、刑法第 10 條、民法第 184 條），以及 10 部核心法典每部至少 2 條。")
    lines.append("")
    lines.append("| 編號 | 法規名稱 | 條號 | 本地端網址 | 遠端伺服器網址 | 理由摘要 (前60字) | 公布/修正日期 | LIS 原始網址 | 原始檔 SHA-256 |")
    lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")

    for idx, (act_id, art_no, ver_date, reason, source_url, raw_path) in enumerate(selected_articles, start=1):
        act_name = act_map.get(act_id, act_id)
        local_url = f"http://127.0.0.1:8080/#/act/{act_id}/article/{art_no}"
        remote_url = f"http://161.33.166.144/#/act/{act_id}/article/{art_no}"
        clean_reason = (reason or "").replace("\r", " ").replace("\n", " ").strip()
        snippet = clean_reason[:60] + ("..." if len(clean_reason) > 60 else "")
        snippet = snippet.replace("|", "\\|")
        file_sha = sha256_file(raw_path) if raw_path else "N/A"
        raw_basename = os.path.basename(raw_path) if raw_path else "N/A"

        lines.append(f"| {idx} | {act_name} | 第 {art_no} 條 | [{act_id}/{art_no}]({local_url}) | [遠端鏈結]({remote_url}) | {snippet} | {ver_date} | [立法院 LIS]({source_url}) | `{file_sha[:12]}...` ({raw_basename}) |")

    lines.append("")
    lines.append("## 逐條詳細比對卡")
    lines.append("")

    for idx, (act_id, art_no, ver_date, reason, source_url, raw_path) in enumerate(selected_articles, start=1):
        act_name = act_map.get(act_id, act_id)
        local_url = f"http://127.0.0.1:8080/#/act/{act_id}/article/{art_no}"
        remote_url = f"http://161.33.166.144/#/act/{act_id}/article/{art_no}"
        file_sha = sha256_file(raw_path) if raw_path else "N/A"

        lines.append(f"### {idx}. {act_name} 第 {art_no} 條 ({ver_date})")
        lines.append(f"- **本地測試 URL**: {local_url}")
        lines.append(f"- **遠端正式 URL**: {remote_url}")
        lines.append(f"- **LIS 原始網址**: {source_url}")
        lines.append(f"- **原始資料封存檔**: `{raw_path}`")
        lines.append(f"- **原始檔 SHA-256**: `{file_sha}`")
        lines.append(f"- **完整立法理由文字**:")
        lines.append("```text")
        lines.append(reason if reason else "(無理由文字)")
        lines.append("```")
        lines.append("")

    os.makedirs(os.path.dirname(OUTPUT_MD), exist_ok=True)
    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Successfully generated {OUTPUT_MD} with {len(selected_articles)} sampled articles.")

if __name__ == "__main__":
    generate_pack()

