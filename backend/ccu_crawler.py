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
                html = resp.read().decode("utf-8", errors="ignore")
            # Extract sample metadata
            results = []
            pattern = re.compile(r'href="([^"]+FINT03\.aspx\?param=[^"]+)"[^>]*>([^<]+)</a>', re.I)
            for m in pattern.findall(html)[:15]:
                link, title = m
                results.append({
                    "source": "法源法律網 (LawBank)",
                    "title": title.strip(),
                    "url": urllib.parse.urljoin(LAWBANK_URL, link),
                    "query": query
                })
            return results
        except Exception as e:
            print(f"Lawbank search error: {e}")
            return []

    def search_lawdata_articles(self, query: str) -> List[Dict[str, Any]]:
        """
        Searches LawData (月旦知識庫) for journal articles and literature.
        """
        if not self.session.get("cookies"):
            return []
        encoded = urllib.parse.quote(query)
        target_url = f"{LAWDATA_URL}anglekmc/ttswebx?@0:0:1:lawkm@@0.1702332962648232?k={encoded}"
        try:
            req = urllib.request.Request(target_url, headers=self.get_headers())
            with urllib.request.urlopen(req, context=self.ctx, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
            results = []
            pattern = re.compile(r'href="([^"]*ttswebx[^"]*)"[^>]*>([^<]+)</a>', re.I)
            for m in pattern.findall(html)[:15]:
                link, title = m
                if "pdf" in link.lower() or "view" in link.lower() or len(title.strip()) > 4:
                    results.append({
                        "source": "月旦知識庫 (LawData)",
                        "title": title.strip(),
                        "url": urllib.parse.urljoin(LAWDATA_URL, link),
                        "query": query
                    })
            return results
        except Exception as e:
            print(f"Lawdata search error: {e}")
            return []

