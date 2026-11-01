"""
Unit tests for Legal Hub models and validations.
"""
import unittest
from backend.models import Act, Article, Attachment, ValidationError


class TestModels(unittest.TestCase):
    def test_attachment_creation_valid(self):
        att = Attachment(
            title="測試附件.pdf",
            file_type="pdf",
            url="https://example.com/test.pdf",
            description="說明"
        )
        self.assertEqual(att.title, "測試附件.pdf")
        self.assertEqual(att.file_type, "PDF")
        self.assertEqual(att.url, "https://example.com/test.pdf")

    def test_attachment_missing_title(self):
        with self.assertRaises(ValidationError):
            Attachment(title="", file_type="PDF", url="https://example.com/test.pdf")

    def test_attachment_missing_url(self):
        with self.assertRaises(ValidationError):
            Attachment(title="測試", file_type="PDF", url="")

    def test_article_creation_valid(self):
        art = Article(
            article_no="185-3",
            title="不能安全駕駛罪",
            content="駕駛動力交通工具而有下列情形之一者...",
            legislative_reasons="保護公眾往來安全",
            lawplayer_link="https://lawplayer.com/act/criminal_code/article_185-3"
        )
        self.assertEqual(art.article_no, "185-3")
        self.assertIn("185-3", art.lawplayer_link)

    def test_article_empty_content(self):
        with self.assertRaises(ValidationError):
            Article(article_no="1", content="")

    def test_article_empty_article_no(self):
        with self.assertRaises(ValidationError):
            Article(article_no="", content="內容")

    def test_duplicate_attachment_in_article(self):
        # Duplicate image/attachment validation in article
        attachments = [
            {"title": "圖檔A", "file_type": "PDF", "url": "https://example.com/same.pdf"},
            {"title": "圖檔B", "file_type": "PDF", "url": "https://example.com/same.pdf"}
        ]
        with self.assertRaises(ValidationError) as ctx:
            Article(article_no="100", content="內容", attachments=attachments)
        self.assertIn("Duplicate attachment URL", str(ctx.exception))

    def test_duplicate_article_in_act(self):
        # Duplicate article validation in act
        articles = [
            {"article_no": "1", "content": "第一條內容"},
            {"article_no": "1", "content": "重疊的第一條內容"}
        ]
        with self.assertRaises(ValidationError) as ctx:
            Act(id="test_act", name="測試法規", articles=articles)
        self.assertIn("Duplicate article number '1'", str(ctx.exception))

    def test_duplicate_attachment_in_act(self):
        # Duplicate image/attachment validation in act
        attachments = [
            {"title": "全法附檔1", "file_type": "PDF", "url": "https://example.com/att.pdf"},
            {"title": "全法附檔2", "file_type": "PDF", "url": "https://example.com/att.pdf"}
        ]
        with self.assertRaises(ValidationError) as ctx:
            Act(id="test_act_att", name="測試附檔法規", attachments=attachments)
        self.assertIn("Duplicate attachment URL", str(ctx.exception))


    def test_article_rich_enrichment_fields(self):
        art = Article(
            article_no="1",
            content="行為之處罰，以行為時之法律有明文規定者為限。",
            title="罪刑法定原則",
            legal_definition="罪刑法定原則為刑法核心基石",
            faqs=[{"q": "Q1 國家可以事後立法定我罪嗎？", "a": "不行"}],
            comparison_table={"headers": ["A", "B"], "rows": [["1", "2"]]},
            official_letters=[{"no": "法檢字第 123 號", "organ": "法務部", "date": "2020-01-01"}]
        )
        d = art.to_dict()
        self.assertEqual(d["legal_definition"], "罪刑法定原則為刑法核心基石")
        self.assertEqual(len(d["faqs"]), 1)
        self.assertEqual(len(d["comparison_table"]["headers"]), 2)
        self.assertEqual(len(d["official_letters"]), 1)


if __name__ == "__main__":
    unittest.main()
