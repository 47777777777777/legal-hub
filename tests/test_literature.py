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
            "title": "論刑法聚眾犯概念與近期相關修法",
            "subtitle": "以妨害秩序罪章為中心",
            "author": "許澤天",
            "author_affiliation": "國立成功大學法律學系教授",
            "journal_name": "台灣法學雜誌",
            "pub_year": 2021,
            "pub_date": "2021-06",
            "volume": "第 394 期",
            "issue": "",
            "pages": "15-28",
            "abstract": "本文針對刑法第149條及第150條聚眾妨害秩序罪之構成要件修法提出學理評析...",
            "abstract_en": "This article examines the recent criminal code amendments...",
            "keywords": ["聚眾犯", "妨害秩序", "刑法第149條", "刑法第150條"],
            "cited_articles": [
                {"act_id": "criminal_code", "article_no": "149"},
                {"act_id": "criminal_code", "article_no": "150"}
            ],
            "cited_judgments": ["最高法院 109 年度台上字第 3381 號判決"],
            "references": ["許澤天，《刑法分則》，2020 年。"],
            "related_literature": [],
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
        self.assertEqual(lit["title"], "論刑法聚眾犯概念與近期相關修法")
        self.assertEqual(lit["author"], "許澤天")
        self.assertEqual(lit["journal_name"], "台灣法學雜誌")
        self.assertEqual(lit["pub_year"], 2021)
        self.assertGreaterEqual(len(lit["cited_articles"]), 2)
        self.assertIn("聚眾犯", lit["keywords"])
        self.assertGreater(lit["file_size_mb"], 1.0)

        # Test querying literature by article (二級維度：刑法第 149 條)
        by_art = self.storage.get_literature_for_article("criminal_code", "149")
        self.assertTrue(len(by_art) >= 1)

    def test_duplicate_prevention_same_title_and_author(self):
        # Enforce rule: 同標題 + 同作者 就不能重複儲存
        dup_payload = {
            "id": "new_id_from_other_source",
            "title": "論刑法聚眾犯概念與近期相關修法",  # Same title
            "author": "許澤天",  # Same author
            "journal_name": "台灣法學雜誌",
            "pub_year": 2021,
            "cited_articles": [{"act_id": "criminal_code", "article_no": "150"}]
        }
        count_before = self.storage.get_literature_stats()["total_articles"]
        res_id = self.storage.add_literature(dup_payload)
        # Must return the existing ID test_lit_2026_001 instead of inserting a new record
        self.assertEqual(res_id, "test_lit_2026_001")
        # Check total count did not increase
        count_after = self.storage.get_literature_stats()["total_articles"]
        self.assertEqual(count_after, count_before)
        # Check cited article 150 was dual-bound to existing record
        by_art_150 = self.storage.get_literature_for_article("criminal_code", "150")
        self.assertEqual(len(by_art_150), 1)
        self.assertEqual(by_art_150[0]["id"], "test_lit_2026_001")

    def test_list_literature_pagination_and_filter(self):
        # Filter by author
        res_author = self.storage.list_literature(author="許澤天")
        self.assertTrue(res_author["total_items"] >= 1)
        self.assertEqual(res_author["items"][0]["author"], "許澤天")

        # Filter by year
        res_year = self.storage.list_literature(year=2021)
        self.assertTrue(res_year["total_items"] >= 1)

        # Filter by act_id and article_no
        res_art = self.storage.list_literature(act_id="criminal_code", article_no="149")
        self.assertTrue(res_art["total_items"] >= 1)

    def test_literature_stats(self):
        stats = self.storage.get_literature_stats()
        self.assertGreaterEqual(stats["total_articles"], 1)
        self.assertGreaterEqual(stats["downloaded_articles"], 1)
        self.assertGreater(stats["downloaded_size_bytes"], 0)
        self.assertGreater(stats["downloaded_size_mb"], 0)
        self.assertGreater(stats["average_file_size_mb"], 0)
        self.assertTrue(any(y["year"] == 2021 for y in stats["year_distribution"]))

    def test_api_literature_routes(self):
        # 1. GET /api/literature
        req = urllib.request.Request(f"{self.base_url}/api/literature?author=%E8%A8%B1%E6%BE%A4%E5%A4%A9")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data.get("success"))
            self.assertTrue(data.get("data", {}).get("total_items") >= 1)

        # 2. GET /api/literature/<id>
        req = urllib.request.Request(f"{self.base_url}/api/literature/test_lit_2026_001")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data.get("success"))
            self.assertEqual(data["data"]["title"], "論刑法聚眾犯概念與近期相關修法")
            self.assertGreaterEqual(len(data["data"]["cited_articles"]), 2)

        # 3. GET /api/literature/stats
        req = urllib.request.Request(f"{self.base_url}/api/literature/stats")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data.get("success"))
            self.assertIn("downloaded_size_mb", data["data"])
            self.assertIn("average_file_size_mb", data["data"])

        # 4. GET /api/acts/criminal_code/articles/149/literature
        req = urllib.request.Request(f"{self.base_url}/api/acts/criminal_code/articles/149/literature")
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
        found = self.storage.find_literature_by_title_author("論刑法聚眾犯概念與近期相關修法", "許澤天")
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

    def test_clear_all_literature(self):
        test_db = os.path.join(os.path.dirname(__file__), "test_clear_isolated.db")
        if os.path.exists(test_db):
            os.remove(test_db)
        isolated_storage = LegalStorage(db_path=test_db)
        isolated_storage.add_literature({
            "id": "iso_001",
            "title": "測試文獻清除",
            "author": "測試作者",
            "journal_name": "測試學報"
        })
        count = isolated_storage.clear_all_literature()
        stats = isolated_storage.get_literature_stats()
        self.assertEqual(stats["total_articles"], 0)
        if os.path.exists(test_db):
            try:
                os.remove(test_db)
            except Exception:
                pass

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

