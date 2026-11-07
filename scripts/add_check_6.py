import os

with open('scripts/verify_integrity.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_check = '''def check_forbidden_strings(base_dir):
    print("[Check 6/6] Checking static/ and backend/ for forbidden synthesized/mock strings...")
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
'''

old_checks_list = '''    checks = [
        check_moj_content_consistency(conn, chlaw_path),
        check_enrichment_sources(conn),
        check_official_letters(conn),
        check_code_lint_handwritten_articles(BASE_DIR),
        check_orphan_enrichments(conn)
    ]'''

new_checks_list = '''    checks = [
        check_moj_content_consistency(conn, chlaw_path),
        check_enrichment_sources(conn),
        check_official_letters(conn),
        check_code_lint_handwritten_articles(BASE_DIR),
        check_orphan_enrichments(conn),
        check_forbidden_strings(BASE_DIR)
    ]'''

content = content.replace('def verify_all():', new_check + '\ndef verify_all():')
content = content.replace(old_checks_list, new_checks_list)
content = content.replace('ALL 5 INTEGRITY CHECKS', 'ALL 6 INTEGRITY CHECKS')

with open('scripts/verify_integrity.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Updated verify_integrity.py cleanly')
