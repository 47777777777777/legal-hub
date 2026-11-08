import sqlite3
import time
import sys
import os

BASE_DIR = r"C:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.compare import diff_tokens, normalize_text_for_compare, is_table_line

def check_all_corpus_invariants(db_path=None):
    db_path = db_path or os.path.join(BASE_DIR, "data", "legal_hub.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Fetch all acts and articles with multiple versions
    print("=== Full Corpus Invariant Check across article_versions ===")
    cur.execute("""
        SELECT act_id, article_no, version_date, content, action_type
        FROM article_versions
        ORDER BY act_id, article_no, version_date ASC
    """)
    rows = cur.fetchall()
    print(f"Total article_versions in DB: {len(rows)}")

    # Group by (act_id, article_no)
    articles_map = {}
    for r in rows:
        key = (r[0], r[1])
        articles_map.setdefault(key, []).append({
            "version_date": r[2],
            "content": r[3] or "",
            "action_type": r[4] or ""
        })

    total_pairs = 0
    checked_pairs = 0
    table_pairs = 0
    violations = []

    start_time = time.time()
    for (act_id, art_no), v_list in articles_map.items():
        if len(v_list) < 2:
            continue
        for i in range(len(v_list) - 1):
            total_pairs += 1
            old_ver = v_list[i]
            new_ver = v_list[i + 1]
            old_c = old_ver["content"]
            new_c = new_ver["content"]

            # If table, skip diff
            if any(is_table_line(l) for l in old_c.splitlines()) or any(is_table_line(l) for l in new_c.splitlines()):
                table_pairs += 1
                continue

            checked_pairs += 1
            try:
                tokens = diff_tokens(old_c, new_c)
                recon_old = "".join(t for op, t in tokens if op in ("equal", "delete"))
                recon_new = "".join(t for op, t in tokens if op in ("equal", "insert"))
                old_norm = normalize_text_for_compare(old_c)
                new_norm = normalize_text_for_compare(new_c)

                if recon_old != old_norm or recon_new != new_norm:
                    violations.append((act_id, art_no, old_ver["version_date"], new_ver["version_date"]))
            except Exception as e:
                violations.append((act_id, art_no, old_ver["version_date"], new_ver["version_date"], str(e)))

    duration = time.time() - start_time
    print(f"Total multi-version pairs: {total_pairs}")
    print(f"  - Table pairs (verbatim side-by-side): {table_pairs}")
    print(f"  - Text pairs checked: {checked_pairs}")
    print(f"  - Invariant violations: {len(violations)}")
    print(f"  - Check duration: {duration:.2f}s")

    if violations:
        print("FAIL: Found invariant violations:")
        for v in violations[:10]:
            print(" ", v)
        return False
    else:
        print(f"PASSED: 100% of {checked_pairs} version pairs strictly satisfy mathematical invariants (0 mismatches).")
        return True

if __name__ == "__main__":
    success = check_all_corpus_invariants()
    sys.exit(0 if success else 1)

