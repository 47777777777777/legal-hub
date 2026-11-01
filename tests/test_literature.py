"""
Comprehensive unit and integration tests for Legal Literature & Dual-Binding Repository.
"""
import unittest
import json
import os
import urllib.request
import threading
from http.server import HTTPServer

from backend.models import Literature, ValidationError
from backend.storage import LegalStorage
from backend.app import LegalApiHandler
from backend.db import get_connection, DB_FILE


class TestLiteratureUnitAndIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.storage = LegalStorage()
        cls.server = HTTPServer(("127.0.0.1", 0), LegalApiHandler)
        cls.port = cls.server.server_port
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        # Insert a sample literature for testing
        self.sample_lit = {
            "id": "test_lit_2026_001",
            "title": "論罪刑法定原則與溯及既往之禁止",
            "subtitle": "以近年大法庭裁定為中心",
            "author": "林山田",
            "author_affiliation": "國立臺灣大學法律學院名譽教授",
            "journal_name": "臺大法學論叢",
            "pub_year": 2026,
            "pub_date": "2026-03",
            "volume": "第 55 卷",
            "issue": "第 1 期",
            "pages": "100-150",
            "abstract": "本文重新審視罪刑法定原則在現代刑事立法之演進與挑戰...",
            "abstract_en": "This article re-examines the principle of legality...",
            "keywords": ["罪刑法定原則", "溯及既往禁止", "刑法第1條", "大法庭裁定"],
            "cited_articles": [
                {"act_id": "criminal_code", "article_no": "1"},
                {"act_id": "criminal_code", "article_no": "2"}
            ],
            "cited_judgments": ["最高法院 110 年度台上大字第 1234 號裁定", "司法院釋字第 777 號解釋"],
            "references": ["林山田，《刑法通論（上冊）》，2008 年。"],
            "related_literature": [
                {"title": "刑法溯及既往原則之新展開", "author": "李茂生", "year": 2024}
            ],
            "file_path": "downloads/ccu/test_lit_2026_001.pdf",
            "file_size_bytes": 1258291,  # ~1.2 MB
            "download_status": "downloaded",
            "source_url": "https://www-lawbank-com-tw.autorpa.lib.ccu.edu.tw:8443/test",
            "source_db": "lawdata"
        }
        self.storage.add_literature(self.sample_lit)

    def test_literature_model_validation(self):
        # Missing id
        with self.assertRaises(ValidationError):
            Literature(id="", title="標題", author="作者", journal_name="學報")
        # Missing title
        with self.assertRaises(ValidationError):
            Literature(id="lit1", title="", author="作者", journal_name="學報")
        # Missing author
        with self.assertRaises(ValidationError):
            Literature(id="lit1", title="標題", author="", journal_name="學報")

    def test_get_and_dual_binding(self):
        lit = self.storage.get_literature("test_lit_2026_001")
        self.assertIsNotNone(lit)
        self.assertEqual(lit["title"], "論罪刑法定原則與溯及既往之禁止")
        self.assertEqual(lit["author"], "林山田")
        self.assertEqual(lit["journal_name"], "臺大法學論叢")
        self.assertEqual(lit["pub_year"], 2026)
        self.assertGreaterEqual(len(lit["cited_articles"]), 2)
        self.assertIn("罪刑法定原則", lit["keywords"])
        self.assertGreater(lit["file_size_mb"], 1.0)

        # Test querying literature by article (二級維度：刑法第 1 條)
        by_art = self.storage.get_literature_for_article("criminal_code", "1")
        self.assertTrue(len(by_art) >= 1)

    def test_duplicate_prevention_same_title_and_author(self):
        # Enforce rule: 同標題 + 同作者 就不能重複儲存
        dup_payload = {
            "id": "new_id_from_other_source",
            "title": "論罪刑法定原則與溯及既往之禁止",  # Same title
            "author": "林山田",  # Same author
            "journal_name": "月旦法學雜誌",
            "pub_year": 2026,
            "cited_articles": [{"act_id": "criminal_code", "article_no": "3"}]
        }
        count_before = self.storage.get_literature_stats()["total_articles"]
        res_id = self.storage.add_literature(dup_payload)
        # Must return the existing ID test_lit_2026_001 instead of inserting a new record
        self.assertEqual(res_id, "test_lit_2026_001")
        # Check total count did not increase
        count_after = self.storage.get_literature_stats()["total_articles"]
        self.assertEqual(count_after, count_before)
        # Check cited article 3 was dual-bound to existing record
        by_art_3 = self.storage.get_literature_for_article("criminal_code", "3")
        self.assertEqual(len(by_art_3), 1)
        self.assertEqual(by_art_3[0]["id"], "test_lit_2026_001")

    def test_list_literature_pagination_and_filter(self):
        # Filter by author
        res_author = self.storage.list_literature(author="林山田")
        self.assertTrue(res_author["total_items"] >= 1)
        self.assertEqual(res_author["items"][0]["author"], "林山田")

        # Filter by year
        res_year = self.storage.list_literature(year=2026)
        self.assertTrue(res_year["total_items"] >= 1)

        # Filter by act_id and article_no
        res_art = self.storage.list_literature(act_id="criminal_code", article_no="1")
        self.assertTrue(res_art["total_items"] >= 1)

    def test_literature_stats(self):
        stats = self.storage.get_literature_stats()
        self.assertGreaterEqual(stats["total_articles"], 1)
        self.assertGreaterEqual(stats["downloaded_articles"], 1)
        self.assertGreater(stats["downloaded_size_bytes"], 0)
        self.assertGreater(stats["downloaded_size_mb"], 0)
        self.assertGreater(stats["average_file_size_mb"], 0)
        self.assertTrue(any(y["year"] == 2026 for y in stats["year_distribution"]))

    def test_api_literature_routes(self):
        # 1. GET /api/literature
        req = urllib.request.Request(f"{self.base_url}/api/literature?author=%E6%9E%97%E5%B1%B1%E7%94%B0")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data.get("success"))
            self.assertTrue(data.get("data", {}).get("total_items") >= 1)

        # 2. GET /api/literature/<id>
        req = urllib.request.Request(f"{self.base_url}/api/literature/test_lit_2026_001")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data.get("success"))
            self.assertEqual(data["data"]["title"], "論罪刑法定原則與溯及既往之禁止")
            self.assertGreaterEqual(len(data["data"]["cited_articles"]), 2)

        # 3. GET /api/literature/stats
        req = urllib.request.Request(f"{self.base_url}/api/literature/stats")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data.get("success"))
            self.assertIn("downloaded_size_mb", data["data"])
            self.assertIn("average_file_size_mb", data["data"])

        # 4. GET /api/acts/criminal_code/articles/1/literature
        req = urllib.request.Request(f"{self.base_url}/api/acts/criminal_code/articles/1/literature")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data.get("success"))
            self.assertTrue(data.get("total") >= 1)
            self.assertEqual(data["data"][0]["id"], "test_lit_2026_001")

        # 5. POST /api/cache/clear
        req = urllib.request.Request(f"{self.base_url}/api/cache/clear", data=b"{}", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data.get("success"))

        # 6. GET /api/ccu/harvest/status
        req = urllib.request.Request(f"{self.base_url}/api/ccu/harvest/status")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data.get("success"))
            self.assertIn("is_running", data["data"])
            self.assertIn("total_in_db", data["data"])

        # 7. POST /api/ccu/harvest/stop
        req = urllib.request.Request(f"{self.base_url}/api/ccu/harvest/stop", data=b"{}", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data.get("success"))
            self.assertIn("progress", data)

        # 8. POST /api/ccu/harvest/start (validation on session check)
        req = urllib.request.Request(f"{self.base_url}/api/ccu/harvest/start", data=b"{}", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            # Either fails with friendly session error or starts if session mocked
            self.assertIn("message", data)
            self.assertIn("progress", data)
            self.assertIn("logs", data["progress"])
            self.assertIn("estimation", data["progress"])

    def test_preflight_title_author_check_and_checkpoint(self):
        # 1. Test storage.find_literature_by_title_author
        found = self.storage.find_literature_by_title_author("論罪刑法定原則與溯及既往之禁止", "林山田")
        self.assertIsNotNone(found)
        self.assertEqual(found["id"], "test_lit_2026_001")

        # 2. Non-existent should return None (0s check before downloading)
        not_found = self.storage.find_literature_by_title_author("不存在的論文標題xyz", "張三")
        self.assertIsNone(not_found)

        # 3. Test BatchHarvester checkpoint & estimation
        from backend.batch_crawler import BatchHarvester
        harvester = BatchHarvester.get_instance()
        status = harvester.get_status()
        self.assertIn("estimation", status)
        self.assertIn("current_year", status)
        self.assertIn("total_skipped_duplicates", status)
        self.assertGreater(status["estimation"]["estimated_10y_gb"], 0)

    def test_ccu_search_returns_local_harvested_articles(self):
        # Insert target literature
        sample = {
            "id": "lawbank_2015_test_evolution",
            "title": "論刑法總則規範在2015年度司法實務之演進",
            "author": "法學論叢專題",
            "journal_name": "法源法律專論",
            "pub_year": 2015,
            "pub_date": "2015",
            "file_size_bytes": 1250000,
            "download_status": "ready"
        }
        self.storage.add_literature(sample)

        # GET /api/ccu/search?q=論刑法總則規範
        import urllib.parse
        q_enc = urllib.parse.quote("論刑法總則規範")
        req = urllib.request.Request(f"{self.base_url}/api/ccu/search?q={q_enc}")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data.get("success"))
            items = data.get("data", [])
            titles = [it.get("title") for it in items]
            self.assertIn("論刑法總則規範在2015年度司法實務之演進", titles)
            target = next(it for it in items if it.get("title") == "論刑法總則規範在2015年度司法實務之演進")
            self.assertTrue(target.get("is_local"))

    def test_curated_theses_volume_across_years(self):
        from backend.batch_crawler import BatchHarvester
        harvester = BatchHarvester.get_instance()
        for y in [2015, 2020, 2025, 2026]:
            theses = harvester._get_curated_theses_for_year(y)
            # Must have substantial volume (at least 80 articles per year)
            self.assertGreaterEqual(len(theses), 80, f"Year {y} should have at least 80 curated articles")
            # Must include major journals
            journals = {t["journal_name"] for t in theses}
            self.assertIn("月旦法學雜誌", journals)
            self.assertIn("臺大法學論叢", journals)
            self.assertIn("政大法學評論", journals)
            self.assertIn("月旦裁判時報", journals)

    def test_semantic_statute_extraction(self):
        from backend.batch_crawler import BatchHarvester
        harvester = BatchHarvester.get_instance()
        # Test explicit article
        res1 = harvester._extract_statute_articles("刑法第185條之3酒駕重大爭點")
        self.assertEqual(res1[0]["article_no"], "185-3")

        # Test semantic keyword
        res2 = harvester._extract_statute_articles("論正當防衛與防衛過當之司法認定")
        art_nos2 = [r["article_no"] for r in res2]
        self.assertIn("23", art_nos2)

        res3 = harvester._extract_statute_articles("詐欺罪與人頭帳戶洗錢防制之主觀犯意")
        art_nos3 = [r["article_no"] for r in res3]
        self.assertIn("339", art_nos3)

        res4 = harvester._extract_statute_articles("犯罪所得沒收新制利得估算之衡平")
        art_nos4 = [r["article_no"] for r in res4]
        self.assertIn("38-1", art_nos4)


if __name__ == "__main__":
    unittest.main()

