"""
REST API and HTTP Web Server for Legal Hub.
"""
import os
import sys
import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
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

        self.send_error_json(404, "Endpoint not found", "NotFound")

    def handle_api_get(self, path: str, query: dict):
        try:
            # GET /api/acts
            if path == "/api/acts":
                acts = storage.list_acts()
                self.send_json(200, {"success": True, "data": acts})
                return

            # GET /api/cache/stats
            if path == "/api/cache/stats":
                stats = storage.cache.stats()
                self.send_json(200, {"success": True, "data": stats})
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
        self.end_headers()
        self.wfile.write(content)


def run_server(port: int = 8080, host: str = "127.0.0.1"):
    server_address = (host, port)
    httpd = HTTPServer(server_address, LegalApiHandler)
    print(f"Legal Hub Server running at http://{host}:{port}/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    run_server()
