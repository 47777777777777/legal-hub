"""
Data models and schema validation for Legal Hub.
"""
from typing import List, Dict, Optional, Any


class ValidationError(Exception):
    pass


class Attachment:
    def __init__(self, title: str, file_type: str, url: str, id: Optional[str] = None,
                 related_article: Optional[str] = None, description: Optional[str] = None):
        if not title or not title.strip():
            raise ValidationError("Attachment title cannot be empty.")
        if not url or not url.strip():
            raise ValidationError("Attachment URL cannot be empty.")
        self.id = id or f"att_{abs(hash(url))}"
        self.title = title.strip()
        self.file_type = (file_type or "PDF").upper().strip()
        self.url = url.strip()
        self.related_article = related_article
        self.description = description or ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "file_type": self.file_type,
            "url": self.url,
            "related_article": self.related_article,
            "description": self.description
        }


class Article:
    def __init__(self, article_no: str, content: str, title: str = "",
                 chapter: str = "", legislative_reasons: str = "",
                 practical_insights: Optional[List[Dict[str, str]]] = None,
                 attachments: Optional[List[Dict[str, Any]]] = None,
                 lawplayer_link: str = "", related_articles: Optional[List[str]] = None):
        if not article_no or not str(article_no).strip():
            raise ValidationError("Article number (article_no) cannot be empty.")
        if not content or not content.strip():
            raise ValidationError(f"Article content cannot be empty for article {article_no}.")

        self.article_no = str(article_no).strip()
        self.title = (title or "").strip()
        self.chapter = (chapter or "").strip()
        self.content = content.strip()
        self.legislative_reasons = (legislative_reasons or "").strip()
        self.practical_insights = practical_insights or []
        self.lawplayer_link = lawplayer_link or f"https://lawplayer.com/act/#article_{self.article_no}"
        self.related_articles = related_articles or []
        
        # Attachments validation (check duplicates)
        self.attachments: List[Attachment] = []
        seen_attachment_urls = set()
        if attachments:
            for att_data in attachments:
                url = att_data.get("url", "").strip()
                if url in seen_attachment_urls:
                    raise ValidationError(f"Duplicate attachment URL '{url}' in article {self.article_no}")
                seen_attachment_urls.add(url)
                self.attachments.append(Attachment(
                    title=att_data.get("title", ""),
                    file_type=att_data.get("file_type", "PDF"),
                    url=url,
                    id=att_data.get("id"),
                    related_article=self.article_no,
                    description=att_data.get("description", "")
                ))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "article_no": self.article_no,
            "title": self.title,
            "chapter": self.chapter,
            "content": self.content,
            "legislative_reasons": self.legislative_reasons,
            "practical_insights": self.practical_insights,
            "lawplayer_link": self.lawplayer_link,
            "related_articles": self.related_articles,
            "attachments": [att.to_dict() for att in self.attachments]
        }


class Act:
    def __init__(self, id: str, name: str, last_modified: str = "",
                 category: str = "", org_reform_notice: str = "",
                 name_en: str = "", history: Optional[List[str]] = None,
                 legislative_process: Optional[List[str]] = None,
                 chapters: Optional[List[Dict[str, Any]]] = None,
                 articles: Optional[List[Dict[str, Any]]] = None,
                 attachments: Optional[List[Dict[str, Any]]] = None):
        if not id or not id.strip():
            raise ValidationError("Act ID cannot be empty.")
        if not name or not name.strip():
            raise ValidationError("Act name cannot be empty.")

        self.id = id.strip()
        self.name = name.strip()
        self.name_en = name_en.strip()
        self.last_modified = last_modified.strip()
        self.category = category.strip()
        self.org_reform_notice = org_reform_notice.strip()
        self.history = history or []
        self.legislative_process = legislative_process or []
        self.chapters = chapters or []

        # Validate duplicate attachments at Act level
        self.attachments: List[Attachment] = []
        seen_act_attachment_urls = set()
        if attachments:
            for att_data in attachments:
                url = att_data.get("url", "").strip()
                if url in seen_act_attachment_urls:
                    raise ValidationError(f"Duplicate attachment URL '{url}' in act {self.id}")
                seen_act_attachment_urls.add(url)
                self.attachments.append(Attachment(
                    title=att_data.get("title", ""),
                    file_type=att_data.get("file_type", "PDF"),
                    url=url,
                    id=att_data.get("id"),
                    related_article=att_data.get("related_article"),
                    description=att_data.get("description", "")
                ))

        # Validate duplicate articles within the act
        self.articles: List[Article] = []
        self.articles_map: Dict[str, Article] = {}
        if articles:
            for art_data in articles:
                art = Article(**art_data)
                if art.article_no in self.articles_map:
                    raise ValidationError(f"Duplicate article number '{art.article_no}' found in act {self.id}")
                self.articles_map[art.article_no] = art
                self.articles.append(art)

    def to_dict(self, include_articles: bool = True) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "name": self.name,
            "name_en": self.name_en,
            "last_modified": self.last_modified,
            "category": self.category,
            "org_reform_notice": self.org_reform_notice,
            "history": self.history,
            "legislative_process": self.legislative_process,
            "chapters": self.chapters,
            "attachments": [att.to_dict() for att in self.attachments],
            "total_articles": len(self.articles)
        }
        if include_articles:
            result["articles"] = [art.to_dict() for art in self.articles]
        return result
