"""
Backend validation and duplicate act/attachment tests.
"""
import unittest
import tempfile
import os
import json
from backend.storage import LegalStorage, StorageError
from backend.models import ValidationError


class TestBackendValidation(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.storage = LegalStorage(self.temp_dir, db_path=self.db_path)

    def tearDown(self):
        for f in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, f))
        os.rmdir(self.temp_dir)

    def test_duplicate_act_id_validation(self):
        # Validation for duplicate act ID
        act_data1 = {
            "id": "act_same",
            "name": "測試法A",
            "articles": [{"article_no": "1", "content": "法A第1條"}]
        }
        act_data2 = {
            "id": "act_same",
            "name": "測試法B",
            "articles": [{"article_no": "1", "content": "法B第1條"}]
        }
        self.storage.add_act(act_data1)
        with self.assertRaises(StorageError) as ctx:
            self.storage.add_act(act_data2)
        self.assertIn("Duplicate act ID 'act_same'", str(ctx.exception))

    def test_duplicate_act_name_validation(self):
        # Validation for duplicate act Name
        act_data1 = {
            "id": "act_1",
            "name": "重複名稱法規",
            "articles": []
        }
        act_data2 = {
            "id": "act_2",
            "name": "重複名稱法規",
            "articles": []
        }
        self.storage.add_act(act_data1)
        with self.assertRaises(StorageError) as ctx:
            self.storage.add_act(act_data2)
        self.assertIn("Duplicate act name '重複名稱法規'", str(ctx.exception))

    def test_backend_empty_act_id_validation(self):
        with self.assertRaises(ValidationError):
            self.storage.add_act({"id": "", "name": "無效ID法規"})

    def test_duplicate_image_attachment_validation(self):
        # Validation rejecting duplicate image/attachments inside an article
        bad_act = {
            "id": "act_dup_img",
            "name": "重複圖檔法規",
            "articles": [
                {
                    "article_no": "1",
                    "content": "條文內容",
                    "attachments": [
                        {"title": "法條流程圖.png", "file_type": "PNG", "url": "https://example.com/flowchart.png"},
                        {"title": "流程圖副本.png", "file_type": "PNG", "url": "https://example.com/flowchart.png"}
                    ]
                }
            ]
        }
        with self.assertRaises(ValidationError) as ctx:
            self.storage.add_act(bad_act)
        self.assertIn("Duplicate attachment URL", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
