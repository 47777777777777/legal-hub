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


if __name__ == "__main__":
    unittest.main()
