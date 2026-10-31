"""
Integration tests for CCU AutoRPA endpoints.
"""
import unittest
import json
import urllib.request
import threading
from http.server import HTTPServer

from backend.app import LegalApiHandler


class TestCCUApiIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), LegalApiHandler)
        cls.port = cls.server.server_port
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_get_ccu_status(self):
        req = urllib.request.Request(f"{self.base_url}/api/ccu/status")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data.get("success"))
            self.assertIn("authenticated", data.get("data", {}))
            self.assertIn("institution", data.get("data", {}))

    def test_get_ccu_documents_list(self):
        req = urllib.request.Request(f"{self.base_url}/api/ccu/documents")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data.get("success"))
            self.assertIsInstance(data.get("data"), list)

    def test_post_ccu_session_empty(self):
        payload = json.dumps({"cookies": ""}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/ccu/session",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data.get("success"))
            self.assertFalse(data.get("data", {}).get("authenticated"))


if __name__ == "__main__":
    unittest.main()
