"""
REST API and HTTP Web Server for Legal Hub.
"""
import os
import sys
import json
import urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Optional

# Setup sys.path so direct execution works
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.storage import LegalStorage, StorageError
from backend.models import ValidationError
from backend.pagination import Paginator, PaginationError

# Setup paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data", "acts")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Initialize storage instance
storage = LegalStorage(DATA_DIR)


class LegalApiHandler(BaseHTTPRequestHandler):
    timeout = 15  # Timeout for slow/stalled client connections

    def send_json(self, status_code: int, data: dict):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, status_code: int, message: str, error_type: str = "Error"):
        self.send_json(status_code, {
            "success": False,
            "error": {
                "type": error_type,
                "message": message
            }
        })

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # API Routes
        if path.startswith("/api/"):
            self.handle_api_get(path, query)
            return

        # Static file serving
        self.handle_static_get(path)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/ccu/session":
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                self.send_error_json(400, "Empty request body.", "BadRequest")
                return
            try:
                body_raw = self.rfile.read(content_length).decode("utf-8")
                payload = json.loads(body_raw)
                cookies = payload.get("cookies", "")
                from backend.ccu_session import CCUSessionManager
                updated_session = CCUSessionManager.save_session(cookies)
                self.send_json(200, {"success": True, "data": updated_session})
            except Exception as e:
                self.send_error_json(500, str(e), "ServerError")
            return

        if path == "/api/cache/clear":
            storage.cache.invalidate()
            self.send_json(200, {"success": True, "message": "快取已清理完畢。"})
            return

        if path == "/api/ccu/harvest/start":
            content_length = int(self.headers.get("Content-Length", 0))
            act_id = "criminal_code"
            reset_cp = False
            if content_length > 0:
                try:
                    body_raw = self.rfile.read(content_length).decode("utf-8")
                    payload = json.loads(body_raw)
                    act_id = payload.get("act_id") or "criminal_code"
                    reset_cp = bool(payload.get("reset_checkpoint", False))
                except Exception:
                    pass
            from backend.batch_crawler import BatchHarvester
            res = BatchHarvester.get_instance().start_harvest(act_id=act_id, reset_checkpoint=reset_cp)
            self.send_json(200, res)
            return

        if path == "/api/ccu/harvest/stop":
            from backend.batch_crawler import BatchHarvester
            res = BatchHarvester.get_instance().stop_harvest()
            self.send_json(200, res)
            return

        if path == "/api/acts":
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                self.send_error_json(400, "Empty request body.", "BadRequest")
                return

            try:
                body_raw = self.rfile.read(content_length).decode("utf-8")
                payload = json.loads(body_raw)
                created_act = storage.add_act(payload)
                self.send_json(201, {
                    "success": True,
                    "data": created_act.to_dict(include_articles=False)
                })
            except ValidationError as e:
                self.send_error_json(400, str(e), "ValidationError")
            except StorageError as e:
                self.send_error_json(409, str(e), "DuplicateError")
            except Exception as e:
                self.send_error_json(500, f"Internal server error: {str(e)}", "ServerError")
            return

        if path == "/api/literature":
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                self.send_error_json(400, "Empty request body.", "BadRequest")
                return
            try:
                body_raw = self.rfile.read(content_length).decode("utf-8")
                payload = json.loads(body_raw)
                lit_id = storage.add_literature(payload)
                self.send_json(201, {"success": True, "data": {"id": lit_id}})
            except ValidationError as e:
                self.send_error_json(400, str(e), "ValidationError")
            except Exception as e:
                self.send_error_json(500, f"Internal server error: {str(e)}", "ServerError")
            return

        self.send_error_json(404, "Endpoint not found", "NotFound")

    def handle_api_get(self, path: str, query: dict):
        try:
            # GET /api/acts (supports ?q=... for full statutes search)
            if path == "/api/acts":
                q = query.get("q", [""])[0]
                acts = storage.list_acts(q)
                self.send_json(200, {"success": True, "data": acts})
                return

            # GET /api/cache/stats
            if path == "/api/cache/stats":
                stats = storage.cache.stats()
                self.send_json(200, {"success": True, "data": stats})
                return

            # GET /api/ccu/status
            if path == "/api/ccu/status":
                from backend.ccu_session import CCUSessionManager
                session_status = CCUSessionManager.load_session()
                self.send_json(200, {"success": True, "data": session_status})
                return

            # GET /api/ccu/documents
            if path == "/api/ccu/documents":
                from backend.ccu_crawler import CCUCrawler
                docs = CCUCrawler().list_archived_documents()
                self.send_json(200, {"success": True, "data": docs})
                return

            # GET /api/ccu/harvest/status
            if path == "/api/ccu/harvest/status":
                from backend.batch_crawler import BatchHarvester
                status = BatchHarvester.get_instance().get_status()
                self.send_json(200, {"success": True, "data": status})
                return

            # GET /api/ccu/search?q=...&source=all|lawbank|lawdata (Integrated Local DB + Remote Proxy)
            if path == "/api/ccu/search":
                q = query.get("q", [""])[0].strip()
                source = query.get("source", ["all"])[0]
                results = []
                seen_titles = set()

                # 1. Search local literature database first (guarantee instant visibility of harvested papers)
                if q:
                    local_res = storage.list_literature(query=q, page=1, page_size=50)
                    for lit in local_res.get("items", []):
                        t = lit.get("title", "").strip()
                        if t and t not in seen_titles:
                            seen_titles.add(t)
                            results.append({
                                "id": lit.get("id"),
                                "title": t,
                                "author": lit.get("author") or "法學學者",
                                "source": f"{lit.get('journal_name', '法學期刊')} ({lit.get('pub_year', '')}年) · 本地已收錄",
                                "source_db": lit.get("source_db") or "local",
                                "url": f"#/act/{lit.get('act_id', 'criminal_code')}/article/{lit.get('article_no', '10')}",
                                "file_size_mb": lit.get("file_size_mb", 1.2),
                                "is_local": True
                            })

                    # Also check if q mentions an article number e.g. "185-3", "10", "第10條"
                    import re
                    art_m = re.search(r'(?:第\s*)?(\d+(?:-\d+|之\d+)?)\s*條?', q)
                    if art_m:
                        raw_no = art_m.group(1).replace("之", "-")
                        art_res = storage.list_literature(act_id="criminal_code", article_no=raw_no, page=1, page_size=50)
                        for lit in art_res.get("items", []):
                            t = lit.get("title", "").strip()
                            if t and t not in seen_titles:
                                seen_titles.add(t)
                                results.append({
                                    "id": lit.get("id"),
                                    "title": t,
                                    "author": lit.get("author") or "法學學者",
                                    "source": f"{lit.get('journal_name', '法學期刊')} ({lit.get('pub_year', '')}年) · 本地已收錄",
                                    "source_db": lit.get("source_db") or "local",
                                    "url": f"#/act/criminal_code/article/{raw_no}",
                                    "file_size_mb": lit.get("file_size_mb", 1.2),
                                    "is_local": True
                                })

                # 2. Query remote AutoRPA proxy if active
                from backend.ccu_crawler import CCUCrawler
                crawler = CCUCrawler()
                remote_items = []
                try:
                    if source in ("all", "lawbank"):
                        remote_items.extend(crawler.search_lawbank_theses(q))
                    if source in ("all", "lawdata"):
                        remote_items.extend(crawler.search_lawdata_articles(q))
                except Exception as e:
                    print(f"Remote proxy search error: {e}")

                for rit in remote_items:
                    t = rit.get("title", "").strip()
                    if t and t not in seen_titles:
                        seen_titles.add(t)
                        results.append(rit)

                self.send_json(200, {"success": True, "data": results, "query": q, "source": source, "total": len(results)})
                return

            # GET /api/literature/stats (文獻儲存與容量統計)
            if path == "/api/literature/stats":
                stats = storage.get_literature_stats()
                self.send_json(200, {"success": True, "data": stats})
                return

            # GET /api/literature (分頁檢索與篩選)
            if path == "/api/literature":
                q = query.get("q", [""])[0]
                author = query.get("author", [""])[0]
                journal = query.get("journal", [""])[0]
                year_str = query.get("year", [""])[0]
                year = int(year_str) if year_str.isdigit() else None
                act_id = query.get("act_id", [""])[0]
                article_no = query.get("article_no", [""])[0]
                page = int(query.get("page", ["1"])[0])
                page_size = int(query.get("page_size", ["20"])[0])
                data = storage.list_literature(
                    query=q, author=author, journal_name=journal, year=year,
                    act_id=act_id, article_no=article_no, page=page, page_size=page_size
                )
                self.send_json(200, {"success": True, "data": data})
                return

            # GET /api/literature/<id>
            if path.startswith("/api/literature/"):
                lit_id = path.split("/api/literature/")[1].strip()
                if lit_id:
                    lit = storage.get_literature(lit_id)
                    if not lit:
                        self.send_error_json(404, f"Literature '{lit_id}' not found.", "NotFound")
                        return
                    self.send_json(200, {"success": True, "data": lit})
                    return

            # Paths like /api/acts/<act_id>...
            parts = [p for p in path.split("/") if p]
            if len(parts) >= 3 and parts[1] == "acts":
                act_id = parts[2]
                act = storage.get_act(act_id)
                if not act:
                    self.send_error_json(404, f"Act with ID '{act_id}' not found.", "NotFound")
                    return

                # GET /api/acts/<act_id>
                if len(parts) == 3:
                    self.send_json(200, {"success": True, "data": act.to_dict(include_articles=True)})
                    return

                sub = parts[3]
                # GET /api/acts/<act_id>/articles
                if sub == "articles":
                    # GET /api/acts/<act_id>/articles/<article_no>/literature (二級維度：法條關聯文獻)
                    if len(parts) == 6 and parts[5] == "literature":
                        art_no = parts[4]
                        lits = storage.get_literature_for_article(act_id, art_no)
                        self.send_json(200, {"success": True, "data": lits, "total": len(lits), "act_id": act_id, "article_no": art_no})
                        return

                    # GET /api/acts/<act_id>/articles/<article_no>
                    if len(parts) == 5:
                        art_no = parts[4]
                        art = storage.get_article(act_id, art_no)
                        if not art:
                            self.send_error_json(404, f"Article '{art_no}' not found in act '{act_id}'.", "NotFound")
                            return
                        self.send_json(200, {"success": True, "data": art.to_dict()})
                        return

                    # Paginated articles
                    page = int(query.get("page", ["1"])[0])
                    page_size = int(query.get("page_size", ["10"])[0])
                    chapter_filter = query.get("chapter", [None])[0]

                    items = [art.to_dict() for art in act.articles]
                    if chapter_filter:
                        items = [a for a in items if chapter_filter in a.get("chapter", "")]

                    paginated = Paginator.paginate(items, page, page_size)
                    self.send_json(200, {"success": True, "data": paginated})
                    return

                # GET /api/acts/<act_id>/search?q=...
                if sub == "search":
                    q = query.get("q", [""])[0]
                    page = int(query.get("page", ["1"])[0])
                    page_size = int(query.get("page_size", ["10"])[0])
                    results = storage.search_articles(act_id, q)
                    paginated = Paginator.paginate(results, page, page_size)
                    self.send_json(200, {"success": True, "data": paginated, "query": q})
                    return

            self.send_error_json(404, "API route not found.", "NotFound")
        except PaginationError as e:
            self.send_error_json(400, str(e), "PaginationError")
        except Exception as e:
            self.send_error_json(500, f"Error: {str(e)}", "ServerError")

    def handle_static_get(self, path: str):
        if path in ("/", "/index.html"):
            filepath = os.path.join(STATIC_DIR, "index.html")
        else:
            rel_path = path.lstrip("/")
            filepath = os.path.join(STATIC_DIR, rel_path)

        filepath = os.path.abspath(filepath)
        # Prevent directory traversal
        if not filepath.startswith(STATIC_DIR) or not os.path.exists(filepath) or os.path.isdir(filepath):
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")
            return

        # Determine MIME type
        content_type = "text/plain"
        if filepath.endswith(".html"):
            content_type = "text/html; charset=utf-8"
        elif filepath.endswith(".css"):
            content_type = "text/css; charset=utf-8"
        elif filepath.endswith(".js"):
            content_type = "application/javascript; charset=utf-8"
        elif filepath.endswith(".json"):
            content_type = "application/json; charset=utf-8"
        elif filepath.endswith(".pdf"):
            content_type = "application/pdf"
        elif filepath.endswith(".svg"):
            content_type = "image/svg+xml"

        with open(filepath, "rb") as f:
            content = f.read()

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()
        self.wfile.write(content)


class ThreadingLegalServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 128


def run_server(port: int = None, host: str = "0.0.0.0"):
    if port is None:
        port = int(os.environ.get("PORT", 8080))
    
    # Auto-seed corpus if empty (e.g. fresh Docker container in Hugging Face Spaces)
    try:
        acts = storage.get_all_acts()
        if len(acts) == 0:
            print("Database empty. Auto-seeding comprehensive legal corpus...")
            import subprocess
            subprocess.run([sys.executable, os.path.join(BASE_DIR, "scripts", "build_comprehensive_corpus.py")], check=True)
            storage.cache.invalidate()
    except Exception as e:
        print(f"Corpus check info: {e}")

    server_address = (host, port)
    httpd = ThreadingLegalServer(server_address, LegalApiHandler)
    print(f"Legal Hub Server running at http://{host}:{port}/")
    print(f"LAN Access for Mobile Phone: http://192.168.1.103:{port}/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    run_server()
