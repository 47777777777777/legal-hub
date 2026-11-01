"""
Integration and API tests for Legal Hub REST endpoints.
"""
import unittest
import threading
import json
import urllib.request
import urllib.error
from http.server import HTTPServer

from backend.app import LegalApiHandler, storage


class TestApiIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start server on an ephemeral port
        cls.server = HTTPServer(("127.0.0.1", 0), LegalApiHandler)
        cls.port = cls.server.server_port
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        # Force reload storage
        storage.load_all_acts()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def get_json(self, path: str):
        # Ensure query parameters with non-ascii characters are URL-quoted
        if "?" in path:
            base, qs = path.split("?", 1)
            parts = qs.split("&")
            encoded_parts = []
            for part in parts:
                if "=" in part:
                    k, v = part.split("=", 1)
                    encoded_parts.append(f"{urllib.parse.quote(k)}={urllib.parse.quote(v)}")
                else:
                    encoded_parts.append(urllib.parse.quote(part))
            full_url = f"{self.base_url}{base}?{'&'.join(encoded_parts)}"
        else:
            full_url = f"{self.base_url}{path}"

        req = urllib.request.Request(full_url)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return resp.status, data

    def post_json(self, path: str, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return resp.status, data
        except urllib.error.HTTPError as e:
            data = json.loads(e.read().decode("utf-8"))
            return e.code, data

    def test_get_acts_list(self):
        status, data = self.get_json("/api/acts")
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])
        acts = data["data"]
        act_ids = [a["id"] for a in acts]
        self.assertIn("criminal_code", act_ids)
        self.assertIn("civil_code", act_ids)

    def test_get_single_act_criminal_code(self):
        status, data = self.get_json("/api/acts/criminal_code")
        self.assertEqual(status, 200)
        act = data["data"]
        self.assertEqual(act["name"], "中華民國刑法")
        self.assertEqual(act["category"], "行政 > 法務部 > 檢察目")
        self.assertEqual(act["last_modified"], "民國 115 年 07 月 22 日")
        self.assertIsInstance(act.get("attachments"), list)

    def test_get_articles_paginated(self):
        status, data = self.get_json("/api/acts/criminal_code/articles?page=1&page_size=2")
        self.assertEqual(status, 200)
        paged = data["data"]
        self.assertEqual(paged["page"], 1)
        self.assertEqual(paged["page_size"], 2)
        self.assertEqual(len(paged["items"]), 2)
        self.assertTrue(paged["has_next"])

    def test_get_single_article_185_3(self):
        status, data = self.get_json("/api/acts/criminal_code/articles/185-3")
        self.assertEqual(status, 200)
        art = data["data"]
        self.assertEqual(art["article_no"], "185-3")
        self.assertIn("尿液或血液所含毒品", art["content"])
        self.assertIsInstance(art["practical_insights"], list)
        self.assertIsInstance(art["attachments"], list)

    def test_get_single_article_1_rich_data(self):
        status, data = self.get_json("/api/acts/criminal_code/articles/1")
        self.assertEqual(status, 200)
        art = data["data"]
        self.assertEqual(art["article_no"], "1")
        self.assertEqual(art["title"], "罪刑法定原則")
        self.assertIsInstance(art["faqs"], list)
        self.assertIsInstance(art["comparison_table"], dict)
        self.assertIsInstance(art["official_letters"], list)

    def test_search_articles(self):
        # Search by keyword "酒駕" or "酒精"
        status, data = self.get_json("/api/acts/criminal_code/search?q=酒精&page=1&page_size=10")
        self.assertEqual(status, 200)
        items = data["data"]["items"]
        self.assertTrue(any(a["article_no"] == "185-3" for a in items))

    def test_search_article_by_number(self):
        status, data = self.get_json("/api/acts/criminal_code/search?q=184&page=1&page_size=10")
        self.assertEqual(status, 200)
        items = data["data"]["items"]
        self.assertTrue(any(a["article_no"] == "184" for a in items))

    def test_get_non_existent_act(self):
        try:
            self.get_json("/api/acts/non_existent_act_xyz")
            self.fail("Expected HTTP 404")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)
            data = json.loads(e.read().decode("utf-8"))
            self.assertFalse(data["success"])

    def test_cache_stats_endpoint(self):
        status, data = self.get_json("/api/cache/stats")
        self.assertEqual(status, 200)
        self.assertIn("hits", data["data"])
        self.assertIn("misses", data["data"])

    def test_post_duplicate_act_returns_409(self):
        # Attempt to create an act with an existing ID
        duplicate_payload = {
            "id": "criminal_code",
            "name": "嘗試覆蓋刑法",
            "articles": []
        }
        status, data = self.post_json("/api/acts", duplicate_payload)
        self.assertEqual(status, 409)
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["type"], "DuplicateError")

    def test_search_statutes_ranking_prioritizes_core_laws(self):
        # 1. Searching for "行政程序" must return "行政程序法" as top 1 (not simplified emergency orders)
        status, data = self.get_json("/api/acts?q=行政程序")
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])
        results = data["data"]
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["id"], "admin_procedure_act")
        self.assertEqual(results[0]["name"], "行政程序法")

        # 2. Searching for "刑法" returns "中華民國刑法" as top 1
        status, data = self.get_json("/api/acts?q=刑法")
        self.assertEqual(status, 200)
        self.assertEqual(data["data"][0]["id"], "criminal_code")

        # 3. Searching for "民法" returns "民法" as top 1
        status, data = self.get_json("/api/acts?q=民法")
        self.assertEqual(status, 200)
        self.assertEqual(data["data"][0]["id"], "civil_code")

    def test_lawplayer_article_titles_cleanliness(self):
        # Verify Criminal Code Art 1 has authentic LawPlayer title
        status, data = self.get_json("/api/acts/criminal_code/articles/1")
        self.assertEqual(status, 200)
        self.assertEqual(data["data"]["title"], "罪刑法定原則")

        # Verify Civil Code Art 1 has authentic LawPlayer title "法源"
        status, data = self.get_json("/api/acts/civil_code/articles/1")
        self.assertEqual(status, 200)
        self.assertEqual(data["data"]["title"], "法源")

        # Verify Labor Standards Act Art 1 has authentic LawPlayer title
        status, data = self.get_json("/api/acts/labor_standards_act/articles/1")
        self.assertEqual(status, 200)
        self.assertEqual(data["data"]["title"], "立法目的暨法律之適用")

        # Verify Company Act Art 2 has authentic LawPlayer title
        status, data = self.get_json("/api/acts/company_act/articles/2")
        self.assertEqual(status, 200)
        self.assertEqual(data["data"]["title"], "公司種類")


if __name__ == "__main__":
    unittest.main()
