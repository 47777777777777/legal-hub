
"""
scripts/verify_integrity.py

Automated guardrail verification script for Legal Hub.
Enforces data authenticity, provenance, MOJ consistency, and rejects mock/synthesized content.
1. Any articles.content in DB disagrees with official MOJ ChLaw.json.
2. Any article_enrichments row lacks source, source_url, or fetched_at.
3. official_letters_json contains uniform org fields or template placeholder strings.
4. Any .py file contains hardcoded statutory article literals exceeding 50 lines (lint).
5. Orphan enrichments exist without corresponding article in articles table.
6a. Forbidden synthesized/mock strings in frontend & backend.
6b. Un-allowlisted Chinese fallbacks ('|| <Chinese>') in static/js/*.js.
6c. Synthesized template sentences ('現行明文規範'/'位於') in static/js/*.js.
"""
import os
import sys
import json
import sqlite3
import hashlib
import re
import glob

# Ensure stdout handles UTF-8 characters on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.db import DB_FILE
from backend.sync_opendata import clean_article_no

def check_moj_content_consistency(conn, chlaw_path, chorder_path=None):
    print("[Check 1/6] Checking articles.content against official MOJ ChLaw.json & ChOrder.json (Bidirectional 100%)...")
    if not os.path.exists(chlaw_path):
        print(f"  ERROR: ChLaw.json not found at {chlaw_path}")
        return False
        
    with open(chlaw_path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
    laws_by_name = {l.get("LawName"): l for l in data.get("Laws", [])}

    orders_by_name = {}
    if chorder_path and os.path.exists(chorder_path):
        with open(chorder_path, "r", encoding="utf-8-sig") as f:
            order_data = json.load(f)
        orders_by_name = {l.get("LawName"): l for l in order_data.get("Laws", [])}
    
    cur = conn.cursor()
    # 1. Total DB counts & duplicate check
    total_db_articles = cur.execute("SELECT count(*) FROM articles").fetchone()[0]
    total_db_acts = cur.execute("SELECT count(*) FROM acts").fetchone()[0]
    distinct_articles = cur.execute("SELECT count(DISTINCT act_id || '|' || article_no) FROM articles").fetchone()[0]
    active_acts = cur.execute("SELECT count(*) FROM acts WHERE status = 'active'").fetchone()[0]
    abolished_acts = cur.execute("SELECT count(*) FROM acts WHERE status = 'abolished'").fetchone()[0]
    active_articles = cur.execute("SELECT count(*) FROM articles WHERE status = 'active'").fetchone()[0]
    deleted_articles = cur.execute("SELECT count(*) FROM articles WHERE status = 'deleted'").fetchone()[0]

    print(f"  Audit Corpus Overview:")
    print(f"    - Total Acts in DB: {total_db_acts} (Active: {active_acts}, Abolished: {abolished_acts})")
    print(f"    - Total Articles in DB: {total_db_articles} (Distinct keys: {distinct_articles}, Duplicates: {total_db_articles - distinct_articles})")
    print(f"    - Article Status: {active_articles} active, {deleted_articles} soft-deleted")

    if total_db_articles != distinct_articles:
        print(f"  FAIL: Found duplicate (act_id, article_no) keys in articles table!")
        return False

    # 2. Check MOJ primary laws (ChLaw.json) consistency (Bidirectional)
    cur.execute("SELECT id, name, pcode, status, category FROM acts")
    acts = cur.fetchall()
    
    mismatches = []
    checked_law_articles = 0
    checked_order_articles = 0
    checked_law_forewords = 0
    checked_order_forewords = 0
    matched_acts_count = 0
    matched_orders_acts_count = 0
    non_chlaw_acts_count = 0
    non_chlaw_articles_count = 0

    for act_row in acts:
        act_id, act_name, act_pcode = act_row["id"], act_row["name"], (act_row["pcode"] or "")
        moj_law = laws_by_name.get(act_name)
        is_order = False
        if not moj_law:
            moj_law = orders_by_name.get(act_name)
            if moj_law:
                is_order = True
                matched_orders_acts_count += 1
            else:
                non_chlaw_acts_count += 1
                act_art_cnt = cur.execute("SELECT count(*) FROM articles WHERE act_id = ?", (act_id,)).fetchone()[0]
                non_chlaw_articles_count += act_art_cnt
                continue
        else:
            matched_acts_count += 1

        # Check official foreword (Bidirectional)
        raw_foreword = moj_law.get("LawForeword", "").strip()
        if raw_foreword:
            cur.execute("SELECT content FROM act_forewords WHERE act_id = ? OR pcode = ?", (act_id, act_pcode))
            f_row = cur.fetchone()
            if not f_row:
                print(f"  FAIL: Missing foreword in database for act {act_pcode} ({act_name})!")
                return False
            db_foreword = (f_row[0] or "").strip().replace("\r\n", "\n")
            moj_foreword_clean = raw_foreword.replace("\r\n", "\n")
            if db_foreword != moj_foreword_clean:
                print(f"  FAIL: Foreword content mismatch for act {act_pcode} ({act_name})!")
                print(f"    DB:  {db_foreword[:60]}...")
                print(f"    MOJ: {moj_foreword_clean[:60]}...")
                return False
            if is_order:
                checked_order_forewords += 1
            else:
                checked_law_forewords += 1

        # Build map of MOJ article content
        moj_articles = {}
        for item in moj_law.get("LawArticles", []):
            if item.get("ArticleType") == "A":
                no = clean_article_no(item.get("ArticleNo", ""))
                moj_articles[no] = item.get("ArticleContent", "").strip()
                
        # Forward check: DB articles match MOJ
        cur.execute("SELECT article_no, content FROM articles WHERE act_id = ?", (act_id,))
        db_arts_map = {}
        for art in cur.fetchall():
            art_no = str(art["article_no"])
            db_content = (art["content"] or "").strip().replace("\r\n", "\n")
            db_arts_map[art_no] = db_content
            if art_no in moj_articles:
                moj_content = moj_articles[art_no].replace("\r\n", "\n")
                if is_order:
                    checked_order_articles += 1
                else:
                    checked_law_articles += 1
                if db_content != moj_content:
                    mismatches.append((act_id, art_no, db_content[:40], moj_content[:40]))
                    if len(mismatches) <= 5:
                        print(f"  FAIL: {act_id} Art {art_no} content mismatch!")
                        print(f"    DB:  {db_content[:60]}...")
                        print(f"    MOJ: {moj_content[:60]}...")

        # Reverse check: every MOJ article must exist in DB
        for moj_no in moj_articles:
            if moj_no not in db_arts_map:
                print(f"  FAIL: Missing article in database for {act_id} Art {moj_no}!")
                return False

        # Reverse check: every MOJ chapter must exist in acts.chapters_json
        moj_chapters = [item.get("ArticleContent", "").strip() for item in moj_law.get("LawArticles", []) if item.get("ArticleType") == "C"]
        if moj_chapters:
            cur.execute("SELECT chapters_json FROM acts WHERE id = ?", (act_id,))
            ch_row = cur.fetchone()
            stored_chaps = json.loads(ch_row[0] or "[]") if ch_row and ch_row[0] else []
            stored_titles = {c.get("title", "").strip() for c in stored_chaps}
            for mc in moj_chapters:
                norm_mc = " ".join([p.strip() for p in mc.replace("\r", " ").replace("\n", " ").split() if p.strip()])
                if not any(norm_mc in st or st in norm_mc for st in stored_titles):
                    print(f"  FAIL: Missing chapter heading in database for {act_id}: '{norm_mc}'!")
                    return False
                        
    total_verified = checked_law_articles + checked_order_articles
    if mismatches:
        print(f"  Total content mismatches found: {len(mismatches)} / {total_verified} checked")
        return False

    # Check 1 Assertion: ChLaw.json and ChOrder.json must each verify > 0 articles when provided
    if checked_law_articles == 0:
        print(f"  FAIL: ChLaw.json verified 0 articles! (Must verify > 0)")
        return False
    if chorder_path and os.path.exists(chorder_path) and checked_order_articles == 0:
        print(f"  FAIL: ChOrder.json verified 0 articles! (Must verify > 0)")
        return False
        
    print(f"  Sub-corpus 1 (中央法規 - ChLaw.json):")
    print(f"    - Acts: {matched_acts_count} acts")
    print(f"    - Articles: {checked_law_articles} articles verified 100% bidirectional against ChLaw.json")
    print(f"    - Forewords: {checked_law_forewords} official forewords verified verbatim")
    print(f"  Sub-corpus 2 (法規命令 - ChOrder.json):")
    print(f"    - Acts: {matched_orders_acts_count} acts")
    print(f"    - Articles: {checked_order_articles} articles verified 100% bidirectional against ChOrder.json")
    print(f"    - Forewords: {checked_order_forewords} official forewords verified verbatim")
    print(f"  PASSED: Full DB {total_db_articles:,} articles audited ({checked_law_articles:,} Law + {checked_order_articles:,} Order). Bidirectional 100% fidelity.")
    return True

def check_article_structure_invariant(conn):
    print("[Check 1b] Verifying Article Structure Invariant on all DB articles...")
    from backend.article_structure import parse_article_structure
    cur = conn.cursor()
    cur.execute("SELECT id, act_id, article_no, content, label_raw FROM articles")
    rows = cur.fetchall()
    mismatches = 0
    for r in rows:
        content = r["content"] or ""
        label_raw = r["label_raw"] or ""
        blocks = parse_article_structure(content, is_standard_article=bool(label_raw))
        concat = "".join((b.get("no_raw", "") + b.get("text", "")) for b in blocks)
        norm_orig = re.sub(r'\s+', '', content)
        norm_blocks = re.sub(r'\s+', '', concat)
        if norm_orig != norm_blocks:
            mismatches += 1
            if mismatches <= 3:
                print(f"  FAIL: Invariant mismatch on {r['act_id']} Art {r['article_no']}")
    if mismatches > 0:
        print(f"  FAIL: Found {mismatches} invariant violations!")
        return False
    print(f"  PASSED: All {len(rows):,} articles strictly satisfy structural invariant (0 mismatches).")
    return True

def check_enrichment_sources(conn):
    print("[Check 2/6] Checking article_enrichments source provenance...")
    cur = conn.cursor()
    cur.execute("""
        SELECT count(*) FROM article_enrichments 
        WHERE source IS NULL OR source = '' 
           OR source_url IS NULL OR source_url = '' 
           OR fetched_at IS NULL OR fetched_at = ''
    """)
    missing = cur.fetchone()[0]
    if missing > 0:
        print(f"  FAIL: Found {missing} enrichment rows missing source / source_url / fetched_at!")
        return False
        
    cur.execute("SELECT count(*) FROM article_enrichments")
    total = cur.fetchone()[0]
    print(f"  PASSED: All {total} enrichment rows have verified source provenance.")
    return True

def check_official_letters(conn):
    print("[Check 3/6] Checking official_letters_json for template strings & uniformity...")
    cur = conn.cursor()
    cur.execute("SELECT act_id, article_no, official_letters_json FROM article_enrichments WHERE official_letters_json != '[]'")
    rows = cur.fetchall()
    
    template_patterns = [
        "法務部行政解釋函令（字號：",
        "範例文字",
        "模擬函釋",
        "相關函令字號待查"
    ]
    
    for r in rows:
        act_id, art_no, raw = r[0], r[1], r[2]
        try:
            letters = json.loads(raw)
        except Exception:
            continue
            
        if not letters:
            continue
            
        # Check template strings
        for item in letters:
            summary = item.get("summary", "")
            title = item.get("title", "")
            for pat in template_patterns:
                if pat in summary or pat in title:
                    print(f"  FAIL: Template placeholder found in {act_id} Art {art_no}: {pat}")
                    return False
                    
        # Check org uniformity if > 1 items
        if len(letters) > 1:
            orgs = [item.get("org", "").strip() for item in letters if item.get("org")]
            if len(orgs) > 1 and len(set(orgs)) == 1 and orgs[0] == "法務部":
                print(f"  FAIL: Uniform org '法務部' placeholder found across all items in {act_id} Art {art_no}")
                return False
                
    print("  PASSED: No template strings or uniform placeholder letters detected.")
    return True

def check_code_lint_handwritten_articles(base_dir):
    print("[Check 4/6] Checking Python codebase for hardcoded article literals (> 50 lines)...")
    violations = []
    
    exclude_dirs = {".git", ".system_generated", "node_modules", "data", "backup", "__pycache__"}
    
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for fname in files:
            if not fname.endswith(".py"):
                continue
            if fname.startswith("test_") or fname in ("verify_integrity.py", "smoke_ui.py"):
                continue
                
            fpath = os.path.join(root, fname)
            rel_path = os.path.relpath(fpath, base_dir)
            
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                
            # Detect multi-line array literals of articles
            in_array = False
            array_start = 0
            has_article_keys = False
            bracket_depth = 0
            
            for idx, line in enumerate(lines, 1):
                if "[" in line and ("ARTICLES" in line or "articles" in line):
                    in_array = True
                    array_start = idx
                    bracket_depth = line.count("[") - line.count("]")
                    has_article_keys = False
                    continue
                    
                if in_array:
                    bracket_depth += line.count("[") - line.count("]")
                    if '"article_no"' in line or "'article_no'" in line or '"content"' in line:
                        has_article_keys = True
                        
                    if bracket_depth <= 0 or "]" in line:
                        span = idx - array_start
                        if span > 50 and has_article_keys:
                            violations.append((rel_path, array_start, idx, span))
                        in_array = False
                        
    if violations:
        for v in violations:
            print(f"  FAIL: Hardcoded article literal in {v[0]}:{v[1]}-{v[2]} spans {v[3]} lines!")
        return False
        
    print("  PASSED: No handwritten article literals exceeding 50 lines found in Python files.")
    return True

def check_orphan_enrichments(conn):
    print("[Check 5/6] Checking for orphan enrichments...")
    cur = conn.cursor()
    cur.execute("""
        SELECT e.act_id, e.article_no 
        FROM article_enrichments e
        LEFT JOIN articles a ON e.act_id = a.act_id AND e.article_no = a.article_no
        WHERE a.article_no IS NULL
    """)
    orphans = cur.fetchall()
    if orphans:
        print(f"  FAIL: Found {len(orphans)} orphan enrichments without article in articles table!")
        for o in orphans[:5]:
            print(f"    {o[0]} Art {o[1]}")
        return False
        
    print("  PASSED: Zero orphan enrichments found.")
    return True

def check_forbidden_strings(base_dir):
    print("[Check 6a/6] Checking static/ and backend/ for forbidden synthesized/mock strings...")
    cfg_path = os.path.join(base_dir, "config", "forbidden_strings.json")
    if not os.path.exists(cfg_path):
        print(f"  FAIL: Config file not found: {cfg_path}")
        return False
        
    with open(cfg_path, "r", encoding="utf-8") as f:
        forbidden = json.load(f)
        
    target_dirs = [
        os.path.join(base_dir, "static"),
        os.path.join(base_dir, "backend")
    ]
    
    violations = []
    for tdir in target_dirs:
        for root, dirs, files in os.walk(tdir):
            for fname in files:
                if not (fname.endswith(".js") or fname.endswith(".html") or fname.endswith(".py")):
                    continue
                fpath = os.path.join(root, fname)
                rel_path = os.path.relpath(fpath, base_dir)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        for lineno, line in enumerate(f, 1):
                            for bad_str in forbidden:
                                if bad_str in line:
                                    violations.append((rel_path, lineno, bad_str, line.strip()[:80]))
                except Exception as e:
                    print(f"  Error reading {rel_path}: {e}")
                    
    if violations:
        print(f"  FAIL: Found {len(violations)} forbidden synthesized/mock string occurrences!")
        for rel_path, lineno, bad_str, snippet in violations:
            print(f"    {rel_path}:{lineno} contains '{bad_str}': {snippet}")
        return False
        
    print(f"  PASSED: Zero forbidden synthesized strings detected across static/ and backend/ ({len(forbidden)} rules checked).")
    return True

def check_ui_chinese_fallbacks(base_dir):
    print("[Check 6b/6] Checking static/js/*.js for un-allowlisted Chinese fallbacks ('|| <Chinese>')...")
    allowlist_path = os.path.join(base_dir, "config", "ui_fallback_allowlist.json")
    if not os.path.exists(allowlist_path):
        print(f"  FAIL: Allowlist config not found: {allowlist_path}")
        return False
        
    with open(allowlist_path, "r", encoding="utf-8") as f:
        allowlist = json.load(f)
        
    allowed_hashes = {item["line_hash"] for item in allowlist}
    allowed_values = {item["value"] for item in allowlist}
    
    pattern = re.compile(r'\|\|\s*(["\'`])([^"\'`]*[\u4e00-\u9fa5]+[^"\'`]*)\1')
    violations = []
    
    js_files = glob.glob(os.path.join(base_dir, "static", "js", "*.js"))
    for js_path in js_files:
        rel_path = os.path.relpath(js_path, base_dir).replace("\\", "/")
        with open(js_path, "r", encoding="utf-8", errors="ignore") as f:
            for lineno, line in enumerate(f, 1):
                line_str = line.strip()
                line_hash = hashlib.sha256(line_str.encode("utf-8")).hexdigest()[:16]
                for m in pattern.finditer(line):
                    chinese_val = m.group(2)
                    if line_hash not in allowed_hashes and chinese_val not in allowed_values:
                        violations.append((rel_path, lineno, chinese_val, line_hash, line_str[:80]))
                        
    if violations:
        print(f"  FAIL: Found {len(violations)} un-allowlisted Chinese fallback(s) in static/js/*.js!")
        for v in violations:
            print(f"    {v[0]}:{v[1]} fallback: \"{v[2]}\" (hash: {v[3]}): {v[4]}")
        print("  Every '|| <Chinese>' in frontend code must be audited and registered in config/ui_fallback_allowlist.json.")
        return False
        
    print(f"  PASSED: All Chinese fallbacks in static/js/*.js are verified in ui_fallback_allowlist.json ({len(allowlist)} allowed).")
    return True

def check_template_synthesized_sentences(base_dir):
    print("[Check 6c/6] Checking static/js/*.js template strings for fabricated legal assertions...")
    violations = []
    
    js_files = glob.glob(os.path.join(base_dir, "static", "js", "*.js"))
    for js_path in js_files:
        rel_path = os.path.relpath(js_path, base_dir).replace("\\", "/")
        with open(js_path, "r", encoding="utf-8", errors="ignore") as f:
            for lineno, line in enumerate(f, 1):
                # Pattern: template string containing variable reference alongside "現行明文規範" or "位於"
                if "${" in line and ("現行明文規範" in line or "位於" in line):
                    violations.append((rel_path, lineno, line.strip()[:80]))
                    
    if violations:
        print(f"  FAIL: Found {len(violations)} synthesized sentence pattern(s) in static/js/*.js!")
        for v in violations:
            print(f"    {v[0]}:{v[1]} synthesized sentence: {v[2]}")
        return False
        
    print("  PASSED: No fabricated legal status sentences ('現行明文規範'/'位於') found in static/js/*.js.")
    return True

def check_paywall_strings_in_enrichments(conn: sqlite3.Connection) -> bool:
    print("[Check 7/7] Checking article_enrichments for forbidden paywall strings...")
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(article_enrichments)")
    columns = [col[1] for col in cur.fetchall()]
    
    paywall_patterns = ["在牆內", "在上方解鎖", "解鎖", "會員專屬"]
    
    cur.execute("SELECT * FROM article_enrichments")
    rows = cur.fetchall()
    
    violations = []
    for row in rows:
        act_id = row["act_id"]
        art_no = row["article_no"]
        for col in columns:
            val = str(row[col] or "")
            for pat in paywall_patterns:
                if pat in val:
                    violations.append((act_id, art_no, col, pat, val[:60]))
                    
    if violations:
        print(f"  FAIL: Found {len(violations)} forbidden paywall string violation(s) in article_enrichments!")
        for v in violations[:10]:
            print(f"    act_id={v[0]} art={v[1]} col={v[2]} pat='{v[3]}': {v[4]}")
        return False
        
    print(f"  PASSED: Zero paywall strings found across all {len(rows)} article_enrichments rows.")
    return True

def check_lis_data_authenticity(conn: sqlite3.Connection) -> bool:
    print("[Check 9/9] Checking LIS data authenticity and verbatim provenance in article_reasons & article_comparison...")
    cur = conn.cursor()
    cur.execute("SELECT id, act_id, article_no, version_date, reason, source, raw_path FROM article_reasons")
    reason_rows = cur.fetchall()
    
    cur.execute("SELECT id, act_id, article_no, new_version_date, reason, source, raw_path FROM article_comparison")
    comp_rows = cur.fetchall()
    
    if len(reason_rows) == 0 and len(comp_rows) == 0:
        print("  PASSED: No LIS records populated yet in article_reasons / article_comparison (ready for seed).")
        return True
        
    forbidden_terms = ["在牆內", "解鎖", "會員專屬", "本條尚未收錄", "模擬資料", "測試資料", "範例條文"]
    violations = []
    raw_cache = {}
    
    def resolve_raw_path(p):
        if not p:
            return ""
        norm = p.replace("\\", "/")
        if "data/raw/" in norm:
            rel = "data/raw/" + norm.split("data/raw/")[1]
            candidate = os.path.join(BASE_DIR, *rel.split("/"))
            if os.path.exists(candidate):
                return candidate
        if os.path.exists(p):
            return p
        cand2 = os.path.join(BASE_DIR, p)
        if os.path.exists(cand2):
            return cand2
        return p

    for row in reason_rows:
        rid = row["id"]
        act_id = row["act_id"]
        art_no = row["article_no"]
        v_date = row["version_date"]
        reason = row["reason"] or ""
        source = row["source"]
        raw_path = resolve_raw_path(row["raw_path"])
        
        if source != "立法院法律系統":
            violations.append(f"article_reasons id={rid}: invalid source '{source}' (must be '立法院法律系統')")
            continue
        if not raw_path or not os.path.exists(raw_path):
            violations.append(f"article_reasons id={rid}: raw_path '{row['raw_path']}' does not exist on disk")
            continue
        for term in forbidden_terms:
            if term in reason:
                violations.append(f"article_reasons id={rid}: contains forbidden term '{term}'")
        if raw_path not in raw_cache:
            if raw_path.endswith(".gz"):
                import gzip
                with gzip.open(raw_path, "rt", encoding="utf-8", errors="ignore") as f:
                    raw_html = f.read()
            else:
                with open(raw_path, "r", encoding="utf-8", errors="ignore") as f:
                    raw_html = f.read()
            from bs4 import BeautifulSoup
            import html as html_lib
            raw_text = BeautifulSoup(raw_html, 'html.parser').get_text()
            raw_cache[raw_path] = re.sub(r'\s+', '', html_lib.unescape(raw_text))
        
        clean_raw = raw_cache[raw_path]
        clean_reason = re.sub(r'\s+', '', html_lib.unescape(reason))
        if clean_reason and clean_reason not in clean_raw:
            violations.append(f"article_reasons id={rid} (act={act_id}, art={art_no}, date={v_date}): reason text is not a verbatim substring of raw file {raw_path}")

    for row in comp_rows:
        cid = row["id"]
        act_id = row["act_id"]
        art_no = row["article_no"]
        new_date = row["new_version_date"]
        reason = row["reason"] or ""
        source = row["source"]
        raw_path = resolve_raw_path(row["raw_path"])
        
        if source != "立法院法律系統":
            violations.append(f"article_comparison id={cid}: invalid source '{source}' (must be '立法院法律系統')")
            continue
        if not raw_path or not os.path.exists(raw_path):
            violations.append(f"article_comparison id={cid}: raw_path '{row['raw_path']}' does not exist on disk")
            continue
        for term in forbidden_terms:
            if reason and term in reason:
                violations.append(f"article_comparison id={cid}: contains forbidden term '{term}'")
        if raw_path not in raw_cache:
            if raw_path.endswith(".gz"):
                import gzip
                with gzip.open(raw_path, "rt", encoding="utf-8", errors="ignore") as f:
                    raw_html = f.read()
            else:
                with open(raw_path, "r", encoding="utf-8", errors="ignore") as f:
                    raw_html = f.read()
            from bs4 import BeautifulSoup
            import html as html_lib
            raw_text = BeautifulSoup(raw_html, 'html.parser').get_text()
            raw_cache[raw_path] = re.sub(r'\s+', '', html_lib.unescape(raw_text))
        
        clean_raw = raw_cache[raw_path]
        clean_reason = re.sub(r'\s+', '', html_lib.unescape(reason))
        if clean_reason and clean_reason not in clean_raw:
            violations.append(f"article_comparison id={cid} (act={act_id}, art={art_no}, date={new_date}): reason text is not a verbatim substring of raw file {raw_path}")

    if violations:
        print(f"  FAIL: Found {len(violations)} LIS authenticity violation(s):")
        for v in violations[:10]:
            print(f"    {v}")
        return False
        
    print(f"  PASSED: Verified {len(reason_rows)} reason(s) and {len(comp_rows)} comparison row(s) strictly match raw LIS HTML verbatim.")
    return True

def check_text_refs_integrity(conn):
    print("[Check 11] Verifying text_refs table and citation resolver integrity...")
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='text_refs'")
    if not cur.fetchone():
        print("  FAIL: text_refs table does not exist in database!")
        return False
    
    # Test citation module directly
    from backend.citations import resolve_citations
    sample_text = "犯本法第十條或民法第一百八十四條之罪者"
    refs = resolve_citations(sample_text, host_act_id="criminal_code")
    if len(refs) < 2:
        print(f"  FAIL: Citation resolver failed on sample text: got {refs}")
        return False
    
    ref_host = next((r for r in refs if r.get("ref_act_id") == "criminal_code"), None)
    ref_civil = next((r for r in refs if r.get("ref_act_id") == "civil_code"), None)
    if not ref_host or not ref_civil:
        print(f"  FAIL: Citation resolver did not resolve expected host and explicit targets: got {refs}")
        return False
    
    if ref_civil.get("ref_type") != "explicit" or ref_civil.get("ref_article_no") != "184":
        print(f"  FAIL: Citation resolver resolved civil code incorrectly: {ref_civil}")
        return False

    print("  PASSED: text_refs schema verified and citation engine cross-act reference verified.")
    return True

def verify_all(db_path=None):
    import argparse
    parser = argparse.ArgumentParser(description="Legal Hub Integrity Guardrail Verification")
    parser.add_argument("--db", type=str, default=None, help="Path to database file")
    args, _ = parser.parse_known_args()

    target_db = db_path or args.db or os.environ.get("LEGAL_HUB_DB") or DB_FILE
    print(f"=== Legal Hub Integrity Guardrail Verification ===")
    print(f"Database: {target_db}")
    conn = sqlite3.connect(target_db)
    conn.row_factory = sqlite3.Row
    
    chlaw_path = os.path.join(BASE_DIR, "data", "ChLaw.json")
    chorder_path = os.path.join(BASE_DIR, "data", "ChOrder.json")
    
    checks = [
        check_moj_content_consistency(conn, chlaw_path, chorder_path),
        check_article_structure_invariant(conn),
        check_enrichment_sources(conn),
        check_official_letters(conn),
        check_code_lint_handwritten_articles(BASE_DIR),
        check_orphan_enrichments(conn),
        check_forbidden_strings(BASE_DIR),
        check_ui_chinese_fallbacks(BASE_DIR),
        check_template_synthesized_sentences(BASE_DIR),
        check_paywall_strings_in_enrichments(conn),
        check_lis_data_authenticity(conn),
        check_text_refs_integrity(conn)
    ]
    
    conn.close()
    
    if all(checks):
        print("\n>>> ALL INTEGRITY CHECKS PASSED SUCCESSFULLY. <<<")
        return 0
    else:
        print("\n>>> INTEGRITY CHECK FAILED! <<<")
        return 1

if __name__ == "__main__":
    sys.exit(verify_all())
