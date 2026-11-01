"""
Legal Hub Data Integrity & Anti-Tampering Verification Script.
Exits with non-zero code if any data integrity or guardrail rule is violated:
1. Any articles.content in DB disagrees with official MOJ ChLaw.json.
2. Any article_enrichments row lacks source, source_url, or fetched_at.
3. official_letters_json contains uniform org fields or template placeholder strings.
4. Any .py file contains hardcoded statutory article literals exceeding 50 lines (lint).
5. Orphan enrichments exist without corresponding article in articles table.
"""
import os
import sys
import json
import sqlite3
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.db import DB_FILE
from backend.sync_opendata import clean_article_no, KNOWN_SLUGS

def check_moj_content_consistency(conn, chlaw_path):
    print("[Check 1/5] Checking articles.content against official MOJ ChLaw.json...")
    if not os.path.exists(chlaw_path):
        print(f"  ERROR: ChLaw.json not found at {chlaw_path}")
        return False
        
    with open(chlaw_path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
        
    laws_by_name = {l.get("LawName"): l for l in data.get("Laws", [])}
    
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM acts")
    acts = cur.fetchall()
    
    mismatches = []
    checked_count = 0
    
    for act_row in acts:
        act_id, act_name = act_row["id"], act_row["name"]
        moj_law = laws_by_name.get(act_name)
        if not moj_law:
            continue
            
        # Build map of MOJ article content
        moj_articles = {}
        for item in moj_law.get("LawArticles", []):
            if item.get("ArticleType") == "A":
                no = clean_article_no(item.get("ArticleNo", ""))
                moj_articles[no] = item.get("ArticleContent", "").strip()
                
        # Compare DB articles
        cur.execute("SELECT article_no, content FROM articles WHERE act_id = ?", (act_id,))
        for art in cur.fetchall():
            art_no = str(art["article_no"])
            db_content = (art["content"] or "").strip().replace("\r\n", "\n")
            if art_no in moj_articles:
                moj_content = moj_articles[art_no].replace("\r\n", "\n")
                checked_count += 1
                if db_content != moj_content:
                    mismatches.append((act_id, art_no, db_content[:40], moj_content[:40]))
                    if len(mismatches) <= 5:
                        print(f"  FAIL: {act_id} Art {art_no} content mismatch!")
                        print(f"    DB:  {db_content[:60]}...")
                        print(f"    MOJ: {moj_content[:60]}...")
                        
    if mismatches:
        print(f"  Total content mismatches found: {len(mismatches)} / {checked_count} checked")
        return False
        
    print(f"  PASSED: {checked_count} articles strictly match official MOJ text.")
    return True

def check_enrichment_sources(conn):
    print("[Check 2/5] Checking article_enrichments source provenance...")
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
    print("[Check 3/5] Checking official_letters_json for template strings & uniformity...")
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
    print("[Check 4/5] Checking Python codebase for hardcoded article literals (> 50 lines)...")
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
                stripped = line.strip()
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
    print("[Check 5/5] Checking for orphan enrichments...")
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

def verify_all():
    print(f"=== Legal Hub Integrity Guardrail Verification ===")
    print(f"Database: {DB_FILE}")
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    
    chlaw_path = os.path.join(BASE_DIR, "data", "ChLaw.json")
    
    checks = [
        check_moj_content_consistency(conn, chlaw_path),
        check_enrichment_sources(conn),
        check_official_letters(conn),
        check_code_lint_handwritten_articles(BASE_DIR),
        check_orphan_enrichments(conn)
    ]
    
    conn.close()
    
    if all(checks):
        print("\n>>> ALL 5 INTEGRITY CHECKS PASSED SUCCESSFULLY. <<<")
        return 0
    else:
        print("\n>>> INTEGRITY CHECK FAILED! <<<")
        return 1

if __name__ == "__main__":
    sys.exit(verify_all())
