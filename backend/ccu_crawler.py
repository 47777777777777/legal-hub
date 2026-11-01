"""
CCU Lawbank & Lawdata Crawler & Automated Document Downloader.
Handles article search, automated captcha solving with ddddocr, and document archiving.
"""
import os
import sys
import re
import json
import time
import ssl
import urllib.request
import urllib.parse
from typing import List, Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.captcha_solver import CaptchaSolver
from backend.ccu_session import CCUSessionManager, LAWBANK_URL, LAWDATA_URL

DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads", "ccu")
INDEX_FILE = os.path.join(BASE_DIR, "data", "ccu_downloads.json")


TOP_LAW_JOURNALS = [
    {"name": "月旦法學雜誌", "path": "anglekmc/lawkm?@59^1869995081^35^^^61A01001A100079739999621^@@767624107"},
    {"name": "國立臺灣大學法學論叢", "path": "anglekmc/lawkm?@59^1869995081^35^^^61A01015A520079734496999^@@915595231"},
    {"name": "政大法學評論", "path": "anglekmc/lawkm?@59^1869995081^35^^^61A01018A460079739999813^@@1317091591"},
    {"name": "東吳法律學報", "path": "anglekmc/lawkm?@59^1869995081^35^^^61A01017A220079736198999^@@649926830"},
    {"name": "臺北大學法學論叢", "path": "anglekmc/lawkm?@59^1869995081^35^^^61A01016A670079739999861^@@1802354939"},
    {"name": "中研院法學期刊", "path": "anglekmc/lawkm?@59^1869995081^35^^^61A01015A011779739999961^@@932724099"},
    {"name": "月旦法學教室", "path": "anglekmc/lawkm?@59^1869995081^35^^^61A01001A110079739999710^@@348594137"},
    {"name": "裁判時報", "path": "anglekmc/lawkm?@59^1869995081^35^^^61A01001A010079739999827^@@2094701808"},
    {"name": "國立中正大學法學集刊", "path": "anglekmc/lawkm?@59^1869995081^35^^^61A01019A510079739999908^@@219540007"},
    {"name": "台灣法學雜誌", "path": "anglekmc/lawkm?@59^1869995081^35^^^61A01112A680079789999583^@@1773154389"},
    {"name": "檢察新論", "path": "anglekmc/lawkm?@59^1869995081^35^^^61A01358A012479739999964^@@632843385"},
    {"name": "全國律師", "path": "anglekmc/lawkm?@59^1869995081^35^^^61A01138A170079736990999^@@47640829"},
    {"name": "犯罪與刑事司法研究", "path": "anglekmc/lawkm?@59^1869995081^35^^^61A01117A117079789999964^@@890434061"}
]


class CCUCrawler:
    def __init__(self):
        os.makedirs(DOWNLOADS_DIR, exist_ok=True)
        self.session = CCUSessionManager.load_session()
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

    def get_headers(self) -> Dict[str, str]:
        cookies = self.session.get("cookies", "")
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Cookie": cookies,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        }

    def list_archived_documents(self) -> List[Dict[str, Any]]:
        """
        Returns list of downloaded and indexed papers/documents.
        """
        if not os.path.exists(INDEX_FILE):
            return []
        try:
            with open(INDEX_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def record_document(self, meta: Dict[str, Any]):
        docs = self.list_archived_documents()
        # Avoid duplicate records
        docs = [d for d in docs if d.get("id") != meta.get("id")]
        docs.insert(0, meta)
        try:
            with open(INDEX_FILE, "w", encoding="utf-8") as f:
                json.dump(docs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error recording document: {e}")

    def solve_captcha_from_url(self, captcha_url: str) -> Optional[str]:
        """
        Fetches captcha image from URL and solves it with CaptchaSolver.
        """
        try:
            req = urllib.request.Request(captcha_url, headers=self.get_headers())
            with urllib.request.urlopen(req, context=self.ctx, timeout=8) as resp:
                img_bytes = resp.read()
            return CaptchaSolver.solve(img_bytes)
        except Exception as e:
            print(f"Failed to fetch or solve captcha: {e}")
            return None

    @staticmethod
    def decode_html(raw_bytes: bytes) -> str:
        for enc in ("utf-8", "cp950", "big5"):
            try:
                return raw_bytes.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
        return raw_bytes.decode("utf-8", errors="ignore")

    @staticmethod
    def is_login_or_error_page(html: str) -> bool:
        if not html or len(html) < 50:
            return True
        keywords = [
            "電子資源查詢系統-登入",
            "idm.lib.ccu.edu.tw",
            "使用者登入",
            "請輸入帳號密碼",
            "cculibsys@ccu.edu.tw",
            "修改個人資料"
        ]
        return any(kw in html for kw in keywords)

    @staticmethod
    def is_valid_article_title(title: str) -> bool:
        if not title or len(title) < 3:
            return False
        blacklist = {"english", "修改個人資料", "登入", "登出", "聯絡我們", "首頁", "回上一頁", "網站導覽", "電子資源"}
        if title.lower() in blacklist or "@" in title or ".edu" in title:
            return False
        return True

    def search_lawbank_theses(self, query: str) -> List[Dict[str, Any]]:
        """
        Searches LawBank for theses, papers, and authoritative opinions.
        """
        if not self.session.get("cookies"):
            return []
        # Construct proxy search request
        encoded = urllib.parse.quote(query)
        target_url = f"{LAWBANK_URL}FINT/FINT02.aspx?KW={encoded}"
        try:
            req = urllib.request.Request(target_url, headers=self.get_headers())
            with urllib.request.urlopen(req, context=self.ctx, timeout=10) as resp:
                html = self.decode_html(resp.read())
            if self.is_login_or_error_page(html):
                return []
            # Extract sample metadata
            results = []
            pattern = re.compile(r'href="([^"]+FINT03\.aspx\?param=[^"]+)"[^>]*>([^<]+)</a>', re.I)
            for m in pattern.findall(html)[:15]:
                link, title = m
                clean_title = re.sub(r'<[^>]+>', '', title).strip()
                if self.is_valid_article_title(clean_title):
                    results.append({
                        "source": "法源法律網 (LawBank)",
                        "title": clean_title,
                        "url": urllib.parse.urljoin(LAWBANK_URL, link),
                        "query": query,
                        "source_db": "lawbank"
                    })
            return results
        except Exception as e:
            print(f"Lawbank search error: {e}")
            return []

    @staticmethod
    def clean_cell(raw_text: str) -> str:
        text = re.sub(r'<[^>]+>', '', raw_text)
        text = re.sub(r'^(?:class|align|style|valign|width|height)=[^\s>]+[\s>]*', '', text, flags=re.I)
        return text.replace('&nbsp;', ' ').strip()

    @staticmethod
    def get_law_journal_catalog() -> List[Dict[str, str]]:
        catalog_file = os.path.join(BASE_DIR, "data", "law_journals.json")
        if os.path.exists(catalog_file):
            try:
                with open(catalog_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        return data
            except Exception:
                pass
        return TOP_LAW_JOURNALS

    _articles_cache = []
    _articles_cache_time = 0

    def fetch_taiwan_law_journals(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Directly harvests peer-reviewed articles from Taiwan's top legal journals
        via CCU LawData (TSSCI law reviews and major professional periodicals).
        """
        if not self.session.get("cookies"):
            return []

        # Return cached if fresh (within 300 seconds)
        import time
        if CCUCrawler._articles_cache and (time.time() - CCUCrawler._articles_cache_time < 300):
            return CCUCrawler._articles_cache[:limit * 10]

        all_articles = []
        journal_list = self.get_law_journal_catalog()
        if limit:
            journal_list = journal_list[:limit]

        for j_entry in journal_list:
            name = j_entry["name"]
            path = j_entry["path"]
            url = urllib.parse.urljoin(LAWDATA_URL, path)
            try:
                req = urllib.request.Request(url, headers=self.get_headers())
                with urllib.request.urlopen(req, context=self.ctx, timeout=12) as resp:
                    html = self.decode_html(resp.read())
                if self.is_login_or_error_page(html):
                    continue

                parts = re.split(r'<td\s+', html, flags=re.I)
                i = 0
                while i < len(parts):
                    p = parts[i]
                    if 'class=tdc2' in p or 'class="tdc2"' in p:
                        title = self.clean_cell(p)
                        link_m = re.search(r'href=[\'"]?([^\s\'">]+)', p)
                        link = urllib.parse.urljoin(LAWDATA_URL, f"anglekmc/{link_m.group(1)}") if link_m else ""
                        
                        journal = name
                        if i + 1 < len(parts) and 'tdc3' in parts[i+1]:
                            cj = self.clean_cell(parts[i+1])
                            if cj:
                                journal = cj

                        author = "法學專論"
                        if i + 2 < len(parts) and 'tdc4' in parts[i+2]:
                            ca = self.clean_cell(parts[i+2])
                            if ca:
                                author = ca

                        pub_date = ""
                        if i + 3 < len(parts) and 'tdc5' in parts[i+3]:
                            pub_date = self.clean_cell(parts[i+3])

                        year_m = re.search(r'(19\d\d|20\d\d)', pub_date)
                        year = int(year_m.group(1)) if year_m else 2026

                        # Extract PDF Link from tdc9
                        pdf_link = ""
                        for j in range(i+1, min(i+8, len(parts))):
                            if 'tdc9' in parts[j]:
                                m_pdf = re.search(r"MM_openBrWindow\(['\"]([^'\"]+)['\"]", parts[j], re.I)
                                if m_pdf:
                                    pdf_link = urllib.parse.urljoin(LAWDATA_URL, f"anglekmc/{m_pdf.group(1)}")
                                break

                        if self.is_valid_article_title(title):
                            all_articles.append({
                                "title": title,
                                "author": author,
                                "journal_name": journal,
                                "pub_date": pub_date,
                                "pub_year": year,
                                "url": link,
                                "pdf_url": pdf_link,
                                "source_db": "lawdata",
                                "source": "月旦知識庫 (LawData)"
                            })
                    i += 1
            except Exception as e:
                print(f"Error fetching journal {name}: {e}")
                continue

        if all_articles:
            CCUCrawler._articles_cache = all_articles
            CCUCrawler._articles_cache_time = time.time()

        return all_articles

    def download_pdf_for_literature(self, lit: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetches the full-text PDF for a literature item using the server's authenticated session,
        caches it locally in downloads/ccu/<id>.pdf, and records it in storage.
        """
        lit_id = lit.get("id")
        if not lit_id:
            return {"success": False, "error": "invalid_id", "message": "文獻編號不存在"}

        # 1. Check local file on disk
        target_path = os.path.join(DOWNLOADS_DIR, f"{lit_id}.pdf")
        rel_path = f"downloads/ccu/{lit_id}.pdf"
        if os.path.exists(target_path) and os.path.getsize(target_path) > 1024:
            with open(target_path, "rb") as f:
                hdr = f.read(5)
            if hdr.startswith(b"%PDF"):
                return {"success": True, "file_path": rel_path, "cached": True}
            else:
                try:
                    os.remove(target_path)
                except Exception:
                    pass

        # 2. Check session
        if not self.session.get("cookies"):
            return {
                "success": False,
                "error": "not_authenticated",
                "message": "中正 AutoRPA 代理尚未連線認證，無法直接調閱全文。請於右上角『中正 AutoRPA 文獻採集』輸入通行證。"
            }

        # 3. Determine download URL
        dl_url = lit.get("pdf_url") or lit.get("source_url")
        if not dl_url:
            return {"success": False, "error": "no_url", "message": "此文獻尚未提供線上全文下載連結"}

        try:
            req = urllib.request.Request(dl_url, headers=self.get_headers())
            with urllib.request.urlopen(req, context=self.ctx, timeout=20) as resp:
                data = resp.read()

            # Check if intercepted by CCU login page
            decoded_snippet = data[:1000].decode("utf-8", errors="ignore")
            if self.is_login_or_error_page(decoded_snippet):
                return {
                    "success": False,
                    "error": "session_expired",
                    "message": "中正 AutoRPA 代理通行證已過期（CCU SSO 要求重新認證），請於右上角『中正 AutoRPA 文獻採集』更新 Session 憑證即可續閱全文。"
                }

            # If HTML returned, check if there is an embedded PDF link
            if not data.startswith(b"%PDF"):
                html_text = self.decode_html(data)
                m_pdf = re.search(r"MM_openBrWindow\(['\"]([^'\"]+)['\"]", html_text, re.I)
                if m_pdf:
                    actual_pdf_url = urllib.parse.urljoin(LAWDATA_URL, f"anglekmc/{m_pdf.group(1)}")
                    try:
                        req2 = urllib.request.Request(actual_pdf_url, headers=self.get_headers())
                        with urllib.request.urlopen(req2, context=self.ctx, timeout=20) as resp2:
                            data = resp2.read()
                    except Exception:
                        pass

            # If it's a PDF stream or file
            if data.startswith(b"%PDF"):
                with open(target_path, "wb") as f:
                    f.write(data)
                from backend.storage import storage
                storage.update_literature_file(lit_id, rel_path, len(data))
                return {"success": True, "file_path": rel_path, "cached": False}
            elif self.is_login_or_error_page(data[:2000].decode("utf-8", errors="ignore")):
                return {
                    "success": False,
                    "error": "session_expired",
                    "message": "中正 AutoRPA 代理通行證已過期，請更新通行證以調閱全文。"
                }
            else:
                return {
                    "success": False,
                    "error": "unsupported_format",
                    "message": "遠端伺服器未返回標準 PDF 檔案"
                }
        except Exception as e:
            return {
                "success": False,
                "error": "download_failed",
                "message": f"全文下載連線失敗: {str(e)}"
            }

    def search_lawdata_articles(self, query: str, limit: int = 8) -> List[Dict[str, Any]]:
        """
        Searches LawData articles matching query, leveraging core journal indexes.
        """
        if not self.session.get("cookies"):
            return []

        # Filter from authentic core legal journals
        core_articles = self.fetch_taiwan_law_journals(limit=limit)
        query_terms = [q.strip() for q in query.split() if len(q.strip()) > 1]
        
        matches = []
        for art in core_articles:
            t = art.get("title", "")
            a = art.get("author", "")
            j = art.get("journal_name", "")
            combined = f"{t} {a} {j}"
            if any(term in combined for term in query_terms) or not query_terms:
                matches.append(art)
        
        return matches

