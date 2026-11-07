"""
scripts/crawl_lawplayer.py

Resumable, polite crawler and parser for authentic LawPlayer content.
Follows all Legal Hub integrity and crawling rules:
- Rate limiting: <= 1 req/sec, 15-25s rest every 200 requests.
- Halts immediately on 403, 429, or Cloudflare challenge (no retries, no bypass).
- Auto-pauses on 5 consecutive network failures.
- Offline cache: stores raw HTML and response headers in data/raw/lawplayer/{pcode}/{article_no}.*
- Offline parser: reparse without network (--reparse).
- Verifies official MOJ article existence; logs orphans to reports/orphans.csv without DB insertion.
- Populates article_enrichments with source, source_url, fetched_at, article_hash (sha256).
- Rejects any paywall marketing text; stores paywalled_counts_json truthfully.
"""

import os
import sys
import time
import json
import random
import hashlib
import sqlite3
import argparse
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "legal_hub.db")
RAW_BASE_DIR = os.path.join(BASE_DIR, "data", "raw", "lawplayer")
ORPHANS_REPORT = os.path.join(BASE_DIR, "reports", "orphans.csv")

PARSER_VERSION = "1.0"
USER_AGENT = "LegalHub-Research/1.0 (+http://161.33.166.144; for personal legal research)"

# Import parser
sys.path.insert(0, BASE_DIR)
from backend.lawplayer.parser import parse_article_page, parse_act_page, FORBIDDEN_PAYWALL_PATTERNS


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_crawl_tables(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS crawl_jobs (
            act_id TEXT NOT NULL,
            article_no TEXT NOT NULL,
            lp_article_url TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            attempts INTEGER NOT NULL DEFAULT 0,
            last_error TEXT DEFAULT '',
            fetched_at TEXT DEFAULT '',
            parser_version TEXT DEFAULT '1.0',
            PRIMARY KEY (act_id, article_no)
        )
    """)
    conn.commit()


def get_act_info(conn: sqlite3.Connection, identifier: str) -> Optional[sqlite3.Row]:
    cur = conn.cursor()
    cur.execute("""
        SELECT a.id, a.name, a.pcode, m.lp_act_url, m.lp_name
        FROM acts a
        LEFT JOIN law_map m ON UPPER(a.pcode) = UPPER(m.pcode)
        WHERE UPPER(a.id) = UPPER(?) OR UPPER(a.pcode) = UPPER(?) OR a.name = ?
    """, (identifier, identifier, identifier))
    return cur.fetchone()


def get_tier1_acts(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    cur = conn.cursor()
    cur.execute("""
        SELECT a.id, a.name, a.pcode, m.lp_act_url, m.lp_name
        FROM law_map m
        JOIN acts a ON UPPER(a.pcode) = UPPER(m.pcode)
        ORDER BY m.rowid ASC
    """)
    return cur.fetchall()


def log_orphan(act_id: str, article_no: str, lp_url: str, title: str):
    os.makedirs(os.path.dirname(ORPHANS_REPORT), exist_ok=True)
    file_exists = os.path.exists(ORPHANS_REPORT)
    with open(ORPHANS_REPORT, "a", encoding="utf-8") as f:
        if not file_exists:
            f.write("act_id,article_no,lp_article_url,title,detected_at\n")
        f.write(f'"{act_id}","{article_no}","{lp_url}","{title}","{datetime.now().isoformat()}"\n')


def fetch_url_polite(url: str) -> Tuple[int, bytes, Dict[str, str]]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.status
            body = resp.read()
            headers = dict(resp.headers)
            return status, body, headers
    except urllib.error.HTTPError as e:
        body = e.read() if hasattr(e, "read") else b""
        headers = dict(e.headers) if hasattr(e, "headers") else {}
        return e.code, body, headers
    except Exception as e:
        return 0, str(e).encode("utf-8"), {}


def check_cloudflare_or_blocked(status: int, body_str: str) -> Optional[str]:
    if status in (403, 429, 503):
        return f"HTTP {status} Access Denied / Rate Limited"
    if "<title>Just a moment...</title>" in body_str or "<title>Attention Required! | Cloudflare</title>" in body_str:
        return "Cloudflare Bot Challenge Detected (Turnstile Block Page)"
    return None


def sync_act_article_jobs(conn: sqlite3.Connection, act_row: sqlite3.Row, force_refresh_act: bool = False) -> int:
    """Ensures all articles from the act page are discovered and loaded into crawl_jobs."""
    pcode = act_row["pcode"]
    act_id = act_row["id"]
    lp_act_url = act_row["lp_act_url"]
    if not lp_act_url:
        print(f"  Warning: No LawPlayer act URL mapped for {pcode} ({act_row['name']})")
        return 0

    act_dir = os.path.join(RAW_BASE_DIR, pcode)
    os.makedirs(act_dir, exist_ok=True)
    act_html_path = os.path.join(act_dir, "act.html")

    possible_act_paths = [
        act_html_path,
        os.path.join(RAW_BASE_DIR, act_id, "act.html"),
        os.path.join(RAW_BASE_DIR, "civil_procedure_code", "cpc_act.html" if act_id == "civil_procedure_code" else ""),
        os.path.join(RAW_BASE_DIR, "civil_procedure_code", "criminal_act.html" if act_id == "criminal_code" else "")
    ]

    existing_path = None
    for p in possible_act_paths:
        if p and os.path.isfile(p):
            existing_path = p
            break

    raw_html = ""
    if existing_path and not force_refresh_act:
        with open(existing_path, "r", encoding="utf-8") as f:
            raw_html = f.read()
    else:
        print(f"  Fetching act page: {lp_act_url} ...")
        status, body, headers = fetch_url_polite(lp_act_url)
        body_str = body.decode("utf-8", errors="replace")
        block_reason = check_cloudflare_or_blocked(status, body_str)
        if block_reason:
            raise RuntimeError(f"Crawling HALTED: {block_reason} on {lp_act_url}")
        if status != 200:
            raise RuntimeError(f"Failed to fetch act page {lp_act_url}: HTTP {status}")
        
        with open(act_html_path, "w", encoding="utf-8") as f:
            f.write(body_str)
        raw_html = body_str
        time.sleep(1.1)

    articles_map = parse_act_page(raw_html, source_url=lp_act_url)
    print(f"  Discovered {len(articles_map)} articles from LawPlayer act page for {act_id} ({act_row['name']}).")

    cur = conn.cursor()
    # Check official MOJ articles in database
    cur.execute("SELECT article_no FROM articles WHERE act_id = ?", (act_id,))
    moj_articles = {r[0] for r in cur.fetchall()}

    new_jobs = 0
    for art_no, info in articles_map.items():
        if art_no not in moj_articles:
            log_orphan(act_id, art_no, info["url"], info["title"])
            status = "orphan"
        else:
            status = "pending"

        cur.execute("""
            INSERT INTO crawl_jobs (act_id, article_no, lp_article_url, status, parser_version)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(act_id, article_no) DO UPDATE SET
                lp_article_url = excluded.lp_article_url
            WHERE crawl_jobs.status NOT IN ('parsed', 'fetched')
        """, (act_id, art_no, info["url"], status, PARSER_VERSION))
        new_jobs += 1

    conn.commit()
    return new_jobs


def parse_and_upsert_article(conn: sqlite3.Connection, act_id: str, article_no: str, raw_html: str, source_url: str, fetched_at: str):
    """Parses raw HTML and upserts into article_enrichments with provenance and hash."""
    cur = conn.cursor()
    
    # 1. Get official MOJ content and calculate sha256 hash
    cur.execute("SELECT content FROM articles WHERE act_id = ? AND article_no = ?", (act_id, article_no))
    moj_row = cur.fetchone()
    if not moj_row:
        # Orphan article, do not insert into enrichments
        log_orphan(act_id, article_no, source_url, "Not found in MOJ articles table")
        return False

    moj_content = moj_row["content"] or ""
    article_hash = hashlib.sha256(moj_content.encode("utf-8")).hexdigest()

    # 2. Parse HTML
    parsed = parse_article_page(raw_html, source_url=source_url)

    # 3. Guardrail validation: assert no paywall strings
    for field_name, field_val in [("title", parsed["title"]), ("summary", parsed["summary"]), ("deep_reading", parsed["deep_reading"])]:
        for pat in FORBIDDEN_PAYWALL_PATTERNS:
            if pat in field_val:
                raise ValueError(f"Integrity guardrail tripped! Found forbidden string '{pat}' in {field_name} for {act_id} Art {article_no}")

    # 4. JSON serialization
    vernacular_qa_json = json.dumps(parsed["vernacular_qa"], ensure_ascii=False)
    practical_insights_json = json.dumps(parsed["judgments"], ensure_ascii=False)
    official_letters_json = json.dumps(parsed["interpretations"], ensure_ascii=False)
    amendment_history_json = json.dumps(parsed["revisions"], ensure_ascii=False)
    paywalled_counts_json = json.dumps(parsed.get("paywalled_counts", {}), ensure_ascii=False)

    # 5. UPSERT into article_enrichments
    cur.execute("""
        INSERT INTO article_enrichments (
            act_id, article_no, summary, vernacular_qa_json, practical_insights_json,
            official_letters_json, amendment_history_json, paywalled_counts_json,
            lawplayer_link, source, source_url, fetched_at, article_hash
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(act_id, article_no) DO UPDATE SET
            summary = excluded.summary,
            vernacular_qa_json = excluded.vernacular_qa_json,
            practical_insights_json = excluded.practical_insights_json,
            official_letters_json = excluded.official_letters_json,
            amendment_history_json = excluded.amendment_history_json,
            paywalled_counts_json = excluded.paywalled_counts_json,
            lawplayer_link = excluded.lawplayer_link,
            source = excluded.source,
            source_url = excluded.source_url,
            fetched_at = excluded.fetched_at,
            article_hash = excluded.article_hash
    """, (
        act_id, article_no, parsed["summary"], vernacular_qa_json, practical_insights_json,
        official_letters_json, amendment_history_json, paywalled_counts_json,
        source_url, "lawplayer", source_url, fetched_at, article_hash
    ))

    # Also update article title in articles table if authentic title was parsed
    if parsed["title"]:
        cur.execute("""
            UPDATE articles
            SET title = ?, title_source = 'lawplayer'
            WHERE act_id = ? AND article_no = ? AND (title IS NULL OR title = '' OR title_source = 'lawplayer')
        """, (parsed["title"], act_id, article_no))

    conn.commit()
    return True


def run_crawler(args):
    conn = get_db()
    init_crawl_tables(conn)

    # Determine target acts
    acts: List[sqlite3.Row] = []
    if args.tier == "1":
        acts = get_tier1_acts(conn)
    elif args.act:
        act = get_act_info(conn, args.act)
        if not act:
            print(f"Error: Act '{args.act}' not found in database or law_map.")
            sys.exit(1)
        acts = [act]
    else:
        # Default to Tier 1
        acts = get_tier1_acts(conn)

    print(f"Targeting {len(acts)} act(s) for crawling/parsing.")

    # Populate jobs for all targeted acts
    for act in acts:
        sync_act_article_jobs(conn, act)

    # If --reparse mode: parse offline cached files only, no network calls
    if args.reparse:
        print("\n=== REPARSE MODE (Offline Only) ===")
        cur = conn.cursor()
        total_reparsed = 0
        for act in acts:
            pcode = act["pcode"]
            act_id = act["id"]
            act_dir = os.path.join(RAW_BASE_DIR, pcode)
            if not os.path.exists(act_dir):
                continue
            cur.execute("SELECT article_no, lp_article_url, fetched_at FROM crawl_jobs WHERE act_id = ? AND status IN ('fetched', 'parsed')", (act_id,))
            rows = cur.fetchall()
            for r in rows:
                art_no = r["article_no"]
                html_path = os.path.join(act_dir, f"{art_no}.html")
                if os.path.exists(html_path):
                    with open(html_path, "r", encoding="utf-8") as f:
                        raw_html = f.read()
                    parse_and_upsert_article(conn, act_id, art_no, raw_html, r["lp_article_url"], r["fetched_at"])
                    total_reparsed += 1
        print(f"Reparse complete. Updated {total_reparsed} articles in article_enrichments.")
        return

    # Select pending or failed jobs
    cur = conn.cursor()
    target_act_ids = [a["id"] for a in acts]
    placeholders = ",".join(["?"] * len(target_act_ids))
    
    cur.execute(f"""
        SELECT act_id, article_no, lp_article_url, status, attempts, fetched_at
        FROM crawl_jobs
        WHERE act_id IN ({placeholders}) AND status NOT IN ('parsed', 'orphan')
        ORDER BY act_id ASC, CAST(article_no AS INTEGER) ASC
    """, target_act_ids)
    pending_jobs = cur.fetchall()

    print(f"\nFound {len(pending_jobs)} pending/resumable article jobs.")

    if args.dry_run:
        print("\n=== DRY RUN MODE ===")
        limit = min(args.limit or 20, len(pending_jobs))
        print(f"Showing first {limit} job(s) planned for execution:")
        for job in pending_jobs[:limit]:
            print(f"  [Plan] Act: {job['act_id']}, Art: {job['article_no']}, URL: {job['lp_article_url']}")
        print(f"\nTotal planned: {len(pending_jobs)} jobs. Dry-run finished without network requests.")
        return

    # Crawl execution loop
    total_to_crawl = len(pending_jobs)
    if args.limit:
        total_to_crawl = min(args.limit, total_to_crawl)
        pending_jobs = pending_jobs[:total_to_crawl]

    print(f"\nStarting crawl of {total_to_crawl} article(s)...")

    consecutive_failures = 0
    requests_count = 0

    for i, job in enumerate(pending_jobs, 1):
        act_id = job["act_id"]
        art_no = job["article_no"]
        url = job["lp_article_url"]
        
        # Look up pcode for folder naming
        cur.execute("SELECT pcode FROM acts WHERE id = ?", (act_id,))
        pcode_row = cur.fetchone()
        pcode = pcode_row[0] if pcode_row else act_id

        art_dir = os.path.join(RAW_BASE_DIR, pcode)
        os.makedirs(art_dir, exist_ok=True)
        html_path = os.path.join(art_dir, f"{art_no}.html")
        meta_path = os.path.join(art_dir, f"{art_no}.meta.json")

        # Rate limiting: polite pause (1.05 - 1.25s)
        time.sleep(random.uniform(1.05, 1.25))
        requests_count += 1

        # Periodic longer pause every 200 requests (15-25s)
        if requests_count % 200 == 0:
            pause_sec = random.randint(15, 25)
            print(f"  [Polite pause] Reached {requests_count} requests. Resting for {pause_sec}s...")
            time.sleep(pause_sec)

        now_iso = datetime.now().isoformat()
        status_code, body_bytes, headers = fetch_url_polite(url)
        body_str = body_bytes.decode("utf-8", errors="replace")

        # Cloudflare / 403 / 429 check
        block_reason = check_cloudflare_or_blocked(status_code, body_str)
        if block_reason:
            err_msg = f"EMERGENCY HALT: {block_reason} on {url}"
            print(f"\n>>> {err_msg} <<<")
            cur.execute("""
                UPDATE crawl_jobs
                SET status = 'failed', attempts = attempts + 1, last_error = ?
                WHERE act_id = ? AND article_no = ?
            """, (err_msg, act_id, art_no))
            conn.commit()
            print("Stopping immediately as required by Common Rules. Report generated.")
            sys.exit(2)

        if status_code != 200:
            consecutive_failures += 1
            err_msg = f"HTTP {status_code}"
            print(f"  [{i}/{total_to_crawl}] FAILED {act_id} Art {art_no}: {err_msg}")
            cur.execute("""
                UPDATE crawl_jobs
                SET status = 'failed', attempts = attempts + 1, last_error = ?
                WHERE act_id = ? AND article_no = ?
            """, (err_msg, act_id, art_no))
            conn.commit()

            if consecutive_failures >= 5:
                print("\n>>> PAUSE: 5 consecutive failures reached. Halting crawl loop. <<<")
                sys.exit(3)
            continue

        # Success
        consecutive_failures = 0
        
        # Save raw files
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(body_str)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({
                "act_id": act_id,
                "article_no": art_no,
                "url": url,
                "status_code": status_code,
                "headers": headers,
                "fetched_at": now_iso
            }, f, ensure_ascii=False, indent=2)

        # Parse & upsert
        try:
            parse_and_upsert_article(conn, act_id, art_no, body_str, url, now_iso)
            cur.execute("""
                UPDATE crawl_jobs
                SET status = 'parsed', attempts = attempts + 1, fetched_at = ?, last_error = ''
                WHERE act_id = ? AND article_no = ?
            """, (now_iso, act_id, art_no))
            conn.commit()
            print(f"  [{i}/{total_to_crawl}] OK {act_id} Art {art_no}")
        except Exception as e:
            print(f"  [{i}/{total_to_crawl}] PARSE ERROR {act_id} Art {art_no}: {e}")
            cur.execute("""
                UPDATE crawl_jobs
                SET status = 'fetched', attempts = attempts + 1, last_error = ?
                WHERE act_id = ? AND article_no = ?
            """, (str(e), act_id, art_no))
            conn.commit()

    conn.close()
    print("\nCrawling batch completed successfully.")


def main():
    parser = argparse.ArgumentParser(description="Legal Hub LawPlayer Resumable Crawler")
    parser.add_argument("--dry-run", action="store_true", help="Simulate execution without sending requests")
    parser.add_argument("--limit", type=int, help="Limit number of articles to crawl")
    parser.add_argument("--act", type=str, help="Target specific act pcode or ID (e.g. B0010001, civil_procedure_code)")
    parser.add_argument("--tier", type=str, choices=["1", "2", "3"], help="Target tier (1 = Tier 1 Acts)")
    parser.add_argument("--resume", action="store_true", default=True, help="Resume pending/failed jobs")
    parser.add_argument("--reparse", action="store_true", help="Reparse locally saved raw files without network")
    args = parser.parse_args()

    run_crawler(args)


if __name__ == "__main__":
    main()
