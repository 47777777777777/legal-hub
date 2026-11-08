import sqlite3
import csv
import os
import sys

BASE_DIR = r"C:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.compare import normalize_text_for_compare

def validate_self_comparison(db_path=None):
    db_path = db_path or os.path.join(BASE_DIR, "data", "legal_hub.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    validation_csv = os.path.join(BASE_DIR, "reports", "self_comparison_validation.csv")
    unlinked_csv = os.path.join(BASE_DIR, "reports", "self_comparison_unlinked.csv")
    os.makedirs(os.path.dirname(validation_csv), exist_ok=True)

    # 1. Fetch all comparison rows
    cur.execute("""
        SELECT act_id, article_no, new_version_date, old_version_date, action_type, new_content, old_content, reason
        FROM article_comparison
        ORDER BY act_id, article_no, new_version_date ASC
    """)
    comp_rows = cur.fetchall()
    print(f"Total LIS comparison rows to validate: {len(comp_rows)}")

    results = []
    matches = 0
    mismatches = 0

    with open(validation_csv, "w", encoding="utf-8", newline="") as f_val:
        writer = csv.writer(f_val)
        writer.writerow(["act_id", "article_no", "new_version_date", "old_version_date", "is_match", "computed_old_text", "lis_old_text", "notes"])

        for row in comp_rows:
            act_id, art_no, new_date, old_date, action_type, new_c, old_c, reason = row
            
            # Find our computed prior version in article_versions
            cur.execute("""
                SELECT version_date, content, action_type
                FROM article_versions
                WHERE act_id = ? AND article_no = ? AND version_date < ?
                ORDER BY version_date DESC
                LIMIT 1
            """, (act_id, art_no, new_date))
            prior = cur.fetchone()

            computed_old = prior[1] if prior else ""
            computed_norm = normalize_text_for_compare(computed_old)
            lis_norm = normalize_text_for_compare(old_c or "")

            is_match = (computed_norm == lis_norm)
            note = ""
            if is_match:
                matches += 1
            else:
                mismatches += 1
                if not computed_norm and not lis_norm:
                    is_match = True
                    matches += 1
                    mismatches -= 1
                    note = "Both empty (newly added)"
                elif not prior:
                    note = f"No prior version in article_versions (newly enacted or branch)"
                else:
                    note = f"Text difference: computed prior len={len(computed_norm)}, lis len={len(lis_norm)}"

            writer.writerow([
                act_id,
                art_no,
                new_date,
                old_date,
                "MATCH" if is_match else "MISMATCH",
                computed_norm,
                lis_norm,
                note
            ])
            results.append((act_id, art_no, new_date, is_match, note))

    # 2. Check for unlinked versions in article_versions
    # Unlinked: amendment versions (not first version) where no prior version exists, or multiple versions on same date
    cur.execute("""
        SELECT act_id, article_no, version_date, count(*)
        FROM article_versions
        GROUP BY act_id, article_no, version_date
        HAVING count(*) > 1
    """)
    same_date_multis = cur.fetchall()

    with open(unlinked_csv, "w", encoding="utf-8", newline="") as f_un:
        writer_un = csv.writer(f_un)
        writer_un.writerow(["act_id", "article_no", "version_date_raw", "reason"])
        for sm in same_date_multis:
            writer_un.writerow([sm[0], sm[1], sm[2], f"Multiple versions ({sm[3]}) on same date"])

    total = matches + mismatches
    match_rate = (matches / total * 100) if total > 0 else 0.0
    print("\n=== Self-Comparison Validation Summary ===")
    print(f"Total Validated: {total}")
    print(f"Matches: {matches}")
    print(f"Mismatches: {mismatches}")
    print(f"Match Rate: {match_rate:.2f}%")
    print(f"Saved: {validation_csv}")
    print(f"Saved: {unlinked_csv}")

    for act_id, art_no, new_date, is_match, note in results:
        status_str = "MATCH" if is_match else "MISMATCH"
        print(f"  [{status_str}] {act_id} Art {art_no} ({new_date}): {note or 'Verbatim identical'}")

    return match_rate, matches, mismatches

if __name__ == "__main__":
    validate_self_comparison()

