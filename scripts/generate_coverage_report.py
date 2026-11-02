"""
scripts/generate_coverage_report.py

Generates coverage reports per act in reports/coverage/{pcode}.md
and summarizes low-coverage articles in reports/low_coverage.md.
"""

import os
import sys
import json
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "legal_hub.db")
REPORTS_DIR = os.path.join(BASE_DIR, "reports", "coverage")
LOW_COVERAGE_PATH = os.path.join(BASE_DIR, "reports", "low_coverage.md")


def generate_reports():
    os.makedirs(REPORTS_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT a.id as act_id, a.name, a.pcode
        FROM acts a
        WHERE a.pcode IN (SELECT pcode FROM law_map)
        ORDER BY a.rowid ASC
    """)
    tier1_acts = cur.fetchall()

    low_coverage_records = []

    print(f"Generating coverage reports for {len(tier1_acts)} Tier 1 acts...")

    for act in tier1_acts:
        act_id = act["act_id"]
        act_name = act["name"]
        pcode = act["pcode"]

        # Fetch MOJ total
        cur.execute("SELECT count(*) FROM articles WHERE act_id = ?", (act_id,))
        moj_total = cur.fetchone()[0]

        # Fetch enrichments
        cur.execute("""
            SELECT 
                a.article_no, a.title, e.summary, e.vernacular_qa_json,
                e.official_letters_json, e.practical_insights_json,
                e.amendment_history_json, e.paywalled_counts_json
            FROM articles a
            LEFT JOIN article_enrichments e ON a.act_id = e.act_id AND a.article_no = e.article_no
            WHERE a.act_id = ?
            ORDER BY CAST(a.article_no AS INTEGER) ASC
        """, (act_id,))
        rows = cur.fetchall()

        has_title = sum(1 for r in rows if r["title"])
        has_summary = sum(1 for r in rows if r["summary"])
        has_qa = sum(1 for r in rows if r["vernacular_qa_json"] and r["vernacular_qa_json"] != "[]")
        has_letters = sum(1 for r in rows if r["official_letters_json"] and r["official_letters_json"] != "[]")
        has_judgments = sum(1 for r in rows if r["practical_insights_json"] and r["practical_insights_json"] != "[]")
        has_revisions = sum(1 for r in rows if r["amendment_history_json"] and r["amendment_history_json"] != "[]")
        
        # Enriched if any field present
        any_enriched = sum(1 for r in rows if (
            r["title"] or r["summary"] or 
            (r["vernacular_qa_json"] and r["vernacular_qa_json"] != "[]") or
            (r["official_letters_json"] and r["official_letters_json"] != "[]") or
            (r["practical_insights_json"] and r["practical_insights_json"] != "[]") or
            (r["amendment_history_json"] and r["amendment_history_json"] != "[]")
        ))

        pct = round((any_enriched / moj_total * 100), 1) if moj_total else 0.0

        # Write per-act report
        report_path = os.path.join(REPORTS_DIR, f"{pcode}.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"# 法規涵蓋率報表: {act_name} ({pcode})\n\n")
            f.write(f"- 法規識別碼: `{act_id}`\n")
            f.write(f"- MOJ 官方總條數: **{moj_total}**\n")
            f.write(f"- 法律人已收錄條數: **{any_enriched}** ({pct}%)\n\n")
            f.write("## 欄位統計\n\n")
            f.write(f"| 項目 | 數量 | 比例 |\n")
            f.write(f"|---|---|---|\n")
            f.write(f"| 官方條文總數 | {moj_total} | 100% |\n")
            f.write(f"| 有真實條標 | {has_title} | {round(has_title/moj_total*100, 1) if moj_total else 0}% |\n")
            f.write(f"| 有重點摘要 | {has_summary} | {round(has_summary/moj_total*100, 1) if moj_total else 0}% |\n")
            f.write(f"| 有白話 Q&A | {has_qa} | {round(has_qa/moj_total*100, 1) if moj_total else 0}% |\n")
            f.write(f"| 有行政函釋 | {has_letters} | {round(has_letters/moj_total*100, 1) if moj_total else 0}% |\n")
            f.write(f"| 有權威判決 | {has_judgments} | {round(has_judgments/moj_total*100, 1) if moj_total else 0}% |\n")
            f.write(f"| 有修法沿革 | {has_revisions} | {round(has_revisions/moj_total*100, 1) if moj_total else 0}% |\n")

        print(f"  [{pcode}] {act_name}: {any_enriched}/{moj_total} ({pct}%)")

        if pct < 50.0:
            low_coverage_records.append({
                "act_id": act_id,
                "name": act_name,
                "pcode": pcode,
                "moj_total": moj_total,
                "enriched": any_enriched,
                "pct": pct
            })

    # Write low coverage summary
    with open(LOW_COVERAGE_PATH, "w", encoding="utf-8") as f:
        f.write("# 低涵蓋率法規與條文分析報表 (Low Coverage Report)\n\n")
        f.write("依據 Prompt 3 要求，列出收錄率低於 50% 之法規與原因分析。\n\n")
        f.write("| 法規名稱 | Pcode | 官方條數 | 已收錄條數 | 涵蓋率 | 原因分析 |\n")
        f.write("|---|---|---|---|---|---|\n")
        for rec in low_coverage_records:
            reason = "尚未全量爬取（依分批抓取策略進行中）" if rec["enriched"] < rec["moj_total"] else "法律人原生無解析（過渡性或附則條文）"
            f.write(f"| {rec['name']} | `{rec['pcode']}` | {rec['moj_total']} | {rec['enriched']} | {rec['pct']}% | {reason} |\n")

    conn.close()
    print(f"Coverage reports generated in {REPORTS_DIR}")
    print(f"Low coverage report saved to {LOW_COVERAGE_PATH}")


if __name__ == "__main__":
    generate_reports()
