"""
Unit tests for CCUSessionManager.
"""
import unittest
import os
import json
from backend.ccu_session import CCUSessionManager, SESSION_FILE


class TestCCUSessionManager(unittest.TestCase):
    def setUp(self):
        self.backup = None
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                self.backup = f.read()

    def tearDown(self):
        if self.backup:
            with open(SESSION_FILE, "w", encoding="utf-8") as f:
                f.write(self.backup)
        elif os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)

    def test_load_session_default(self):
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
        sess = CCUSessionManager.load_session()
        self.assertFalse(sess["authenticated"])
        self.assertEqual(sess["cookies"], "")

    def test_save_empty_session(self):
        sess = CCUSessionManager.save_session("")
        self.assertFalse(sess["authenticated"])
        self.assertEqual(sess["cookies"], "")

    def test_clean_cookie_input_formats(self):
        # 1. Bare token
        res1 = CCUSessionManager.clean_cookie_input("mgw0fifytmkbv0kvvgku73lrougb8jzs")
        self.assertEqual(res1, "sessionid=mgw0fifytmkbv0kvvgku73lrougb8jzs")

        # 2. Leading 'Cookie:'
        res2 = CCUSessionManager.clean_cookie_input("Cookie: sessionid=xyz123; foo=bar")
        self.assertEqual(res2, "sessionid=xyz123; foo=bar")

        # 3. cURL command
        curl_cmd = "curl 'https://autorpa.lib.ccu.edu.tw' -H 'Cookie: sessionid=test789; csrftoken=abc'"
        res3 = CCUSessionManager.clean_cookie_input(curl_cmd)
        self.assertEqual(res3, "sessionid=test789; csrftoken=abc")

        # 4. Multi-line headers (Copy request headers)
        multi_headers = "accept: text/html\r\ncookie: flysheet-proxy=8eb292; lawbank=af7c\r\nuser-agent: curl"
        res4 = CCUSessionManager.clean_cookie_input(multi_headers)
        self.assertEqual(res4, "flysheet-proxy=8eb292; lawbank=af7c")

        # 5. Hint on missing proxy credentials
        sess = CCUSessionManager.save_session("_ga=12345; _gid=67890")
        self.assertFalse(sess["authenticated"])
        self.assertTrue("flysheet-proxy" in sess.get("hint", "").lower() or "sessionid" in sess.get("hint", "").lower())

        # 6. Hint on Accept header
        sess_accept = CCUSessionManager.save_session("accept: text/html,application/xhtml+xml")
        self.assertFalse(sess_accept["authenticated"])
        self.assertIn("accept", sess_accept.get("hint", "").lower())


if __name__ == "__main__":
    unittest.main()

