import os
import sys
import re
import time
import json
import gzip
import hashlib
import sqlite3
import socket
import urllib.request
import urllib.parse
from http.cookiejar import CookieJar
from bs4 import BeautifulSoup

# Force IPv4 resolution to prevent 21-second TCP connect timeout on dead IPv6 address (2001:4420:601b:2::ac8:c069)
orig_getaddrinfo = socket.getaddrinfo
def getaddrinfo_ipv4(host, port, family=0, type=0, proto=0, flags=0):
    return orig_getaddrinfo(host, port, family=socket.AF_INET, type=type, proto=proto, flags=flags)
socket.getaddrinfo = getaddrinfo_ipv4

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.lis.parser import parse_full_act_reasons, parse_lis_article_no
from backend.db import DB_FILE

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 LegalHub/1.0"
RAW_GZ_DIR = os.path.join(BASE_DIR, "data", "raw", "lis", "gz")
REPORTS_DIR = os.path.join(BASE_DIR, "reports", "lis_coverage")
NO_FULLPAGE_CSV = os.path.join(BASE_DIR, "reports", "lis_no_fullpage.csv")
os.makedirs(RAW_GZ_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

class LisCrawler:
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_FILE
        self.cj = CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cj))
        self.last_req_time = 0.0

    def _throttle(self, min_interval=1.1):
        elapsed = time.time() - self.last_req_time
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self.last_req_time = time.time()

    def fetch_url(self, url, data=None, headers=None, timeout=25):
        self._throttle()
        req_headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8"
        }
        if headers:
            req_headers.update(headers)
        req = urllib.request.Request(url, data=data, headers=req_headers)
        try:
            with self.opener.open(req, timeout=timeout) as resp:
                status = resp.status
                body = resp.read()
                final_url = resp.geturl()
                return status, body, final_url
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                print(f"[CRITICAL STOP] Received HTTP {e.code} on {url}. Stopping immediately per safety policy!")
                sys.exit(2)
            raise e

    def crawl_act(self, law_name, act_id, pcode):
        start_time = time.time()
        req_count = 0

        # Step 1: Entry portal
        entry_url = "https://lis.ly.gov.tw/lglawc/lglawkm"
        status1, body1, _ = self.fetch_url(entry_url)
        req_count += 1
        html1 = body1.decode('utf-8', errors='ignore')

        soup1 = BeautifulSoup(html1, 'html.parser')
        form = soup1.find('form')
        action = form.get('action', '/lglawc/lglawkm') if form else '/lglawc/lglawkm'
        if not action.startswith('http'):
            action = f"https://lis.ly.gov.tw{action}"
        info_val = form.find('input', {'name': 'INFO'}).get('value', '') if form and form.find('input', {'name': 'INFO'}) else ''

        # Step 2: Search by law name
        post_data = {
            'INFO': info_val,
            '@_1_6_T': 'T_LN/LW',
            '_1_6_T': law_name,
            '_IMG_檢索.x': '10',
            '_IMG_檢索.y': '10'
        }
        encoded = urllib.parse.urlencode(post_data).encode('utf-8')
        status2, body2, current_url2 = self.fetch_url(
            action, data=encoded,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": entry_url
            }
        )
        req_count += 1
        html2 = body2.decode('utf-8', errors='ignore')

        # Check for captcha or blocking page
        if "驗證碼" in html2 or "請輸入圖形文字" in html2:
            print(f"[CRITICAL STOP] Captcha encountered while crawling '{law_name}'. Stopping immediately!")
            sys.exit(3)

        # Look for '法條沿革' (Full act reasons link)
        soup2 = BeautifulSoup(html2, 'html.parser')
        history_link = None
        for a in soup2.find_all('a'):
            txt = a.get_text(strip=True)
            if '法條沿革' in txt:
                history_link = a.get('href')
                break

        # If not found directly, find exact match in search results table
        if not history_link:
            for a in soup2.find_all('a'):
                txt = a.get_text(strip=True)
                href = a.get('href', '')
                if (law_name in txt or txt == law_name) and 'lawsingle' in href:
                    law_link = href if href.startswith('http') else f"https://lis.ly.gov.tw{href}"
                    status_sub, body_sub, _ = self.fetch_url(law_link)
                    req_count += 1
                    html_sub = body_sub.decode('utf-8', errors='ignore')
                    soup_sub = BeautifulSoup(html_sub, 'html.parser')
                    for a_h in soup_sub.find_all('a'):
                        if '法條沿革' in a_h.get_text(strip=True):
                            history_link = a_h.get('href')
                            break
                    break

        duration = time.time() - start_time

        if not history_link:
            # Record in lis_no_fullpage.csv
            with open(NO_FULLPAGE_CSV, "a", encoding="utf-8") as f:
                f.write(f"{act_id},{pcode},{law_name},no_history_link\n")
            return {
                "success": False,
                "error": "no_fullpage",
                "req_count": req_count,
                "duration": duration,
                "file_size": 0,
                "reasons_count": 0
            }

        if not history_link.startswith('http'):
            history_link = f"https://lis.ly.gov.tw{history_link}"

        # Step 3: Fetch full act reasons page
        status3, body3, final_url3 = self.fetch_url(history_link)
        req_count += 1
        raw_size = len(body3)

        # Save gzip compressed raw HTML
        gz_filename = f"{pcode}.html.gz"
        gz_path = os.path.join(RAW_GZ_DIR, gz_filename)
        with gzip.open(gz_path, "wb") as gz_f:
            gz_f.write(body3)
        gz_size = os.path.getsize(gz_path)
        sha256 = hashlib.sha256(body3).hexdigest()

        # Parse reasons
        full_html = body3.decode('utf-8', errors='ignore')
        parsed = parse_full_act_reasons(
            full_html,
            raw_path=os.path.relpath(gz_path, BASE_DIR).replace("\\", "/"),
            source_url=final_url3
        )

        total_duration = time.time() - start_time
        return {
            "success": True,
            "act_id": act_id,
            "pcode": pcode,
            "law_name": law_name,
            "req_count": req_count,
            "duration": total_duration,
            "raw_size": raw_size,
            "gz_size": gz_size,
            "sha256": sha256,
            "reasons": parsed,
            "reasons_count": len(parsed),
            "final_url": final_url3,
            "gz_relpath": os.path.relpath(gz_path, BASE_DIR).replace("\\", "/")
        }

    def ingest_act(self, crawl_result):
        if not crawl_result.get("success"):
            return False

        act_id = crawl_result["act_id"]
        reasons = crawl_result["reasons"]
        gz_relpath = crawl_result["gz_relpath"]
        final_url = crawl_result["final_url"]

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        try:
            # Transaction per act
            cur.execute("BEGIN TRANSACTION;")

            # Delete old LIS reasons for this act
            cur.execute("DELETE FROM article_reasons WHERE act_id = ? AND source = '立法院法律系統'", (act_id,))

            inserted = 0
            distinct_arts = set()
            # Delete old LIS versions for this act
            cur.execute("DELETE FROM article_versions WHERE act_id = ? AND source = '立法院法律系統'", (act_id,))

            for r in reasons:
                art_no = r["article_no"]
                v_date = r["version_date"]
                action_type = r.get("action_type", "")
                reason_text = r.get("reason", "")
                content_text = r.get("content", "")
                date_label = r.get("date_label_raw", f"({v_date} {action_type})")
                art_at_time = r.get("article_no_at_the_time", art_no)

                if reason_text:
                    cur.execute("""
                        INSERT INTO article_reasons (
                            act_id, article_no, version_date, action_type, reason,
                            date_label_raw, date_raw, article_no_at_the_time, source_mode,
                            source, source_url, raw_path, fetched_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    """, (
                        act_id, art_no, v_date, action_type, reason_text,
                        date_label, v_date, art_at_time, "fullpage",
                        "立法院法律系統", final_url, gz_relpath
                    ))
                    inserted += 1
                    distinct_arts.add(art_no)

                if content_text:
                    cur.execute("""
                        INSERT INTO article_versions (
                            act_id, article_no, version_date, action_type, content,
                            date_label_raw, date_raw, article_no_at_the_time, source_mode,
                            source, source_url, raw_path, fetched_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    """, (
                        act_id, art_no, v_date, action_type, content_text,
                        date_label, v_date, art_at_time, "fullpage",
                        "立法院法律系統", final_url, gz_relpath
                    ))

            # Record in source_attempts
            cur.execute("""
                INSERT INTO source_attempts (
                    source, act_id, article_no, status, error_reason, duration_ms, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                "lis", act_id, "*", "found" if inserted > 0 else "no_data",
                None, int(crawl_result["duration"] * 1000)
            ))

            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error ingesting {act_id}: {e}")
            raise e
        finally:
            conn.close()

if __name__ == "__main__":
    crawler = LisCrawler()
    res = crawler.crawl_act("行政程序法", "admin_procedure_act", "A0030109")
    print("Test APA crawl:", res["success"], "reasons:", res["reasons_count"], "gz_size:", res["gz_size"], "time:", round(res["duration"], 2))
