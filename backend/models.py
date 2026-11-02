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
                 lawplayer_link: str = "", related_articles: Optional[List[str]] = None,
                 summary: str = "", reading_time: str = "",
                 vernacular_qa: Optional[List[Dict[str, str]]] = None,
                 elements: Optional[List[str]] = None,
                 key_issues: Optional[List[str]] = None,
                 amendment_history: Optional[List[Dict[str, Any]]] = None,
                 faqs: Optional[List[Dict[str, str]]] = None,
                 comparison_table: Optional[Dict[str, Any]] = None,
                 legal_definition: str = "",
                 flowchart: Optional[Dict[str, Any]] = None,
                 official_letters: Optional[List[Dict[str, str]]] = None,
                 title_source: str = "", source: str = "", source_url: str = "",
                 fetched_at: str = "", article_hash: str = "",
                 paywalled_counts: Optional[Dict[str, Any]] = None):
        if not article_no or not str(article_no).strip():
            raise ValidationError("Article number (article_no) cannot be empty.")
        if not content or not content.strip():
            raise ValidationError(f"Article content cannot be empty for article {article_no}.")

        self.article_no = str(article_no).strip()
        self.title = (title or "").strip()
        self.title_source = (title_source or "").strip()
        self.chapter = (chapter or "").strip()
        self.content = content.strip()
        self.legislative_reasons = (legislative_reasons or "").strip()
        self.practical_insights = practical_insights or []
        self.lawplayer_link = (lawplayer_link or "").strip()
        self.related_articles = related_articles or []
        self.summary = summary or ""
        self.reading_time = reading_time or ""
        self.vernacular_qa = vernacular_qa or []
        self.elements = elements or []
        self.key_issues = key_issues or []
        self.amendment_history = amendment_history or []
        self.faqs = faqs or []
        self.comparison_table = comparison_table or {}
        self.legal_definition = legal_definition or ""
        self.flowchart = flowchart or {}
        self.official_letters = official_letters or []
        self.source = (source or "").strip()
        self.source_url = (source_url or "").strip()
        self.fetched_at = (fetched_at or "").strip()
        self.article_hash = (article_hash or "").strip()
        self.paywalled_counts = paywalled_counts or {}
        
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
            "summary": self.summary,
            "reading_time": self.reading_time,
            "vernacular_qa": self.vernacular_qa,
            "elements": self.elements,
            "key_issues": self.key_issues,
            "amendment_history": self.amendment_history,
            "faqs": self.faqs,
            "comparison_table": self.comparison_table,
            "legal_definition": self.legal_definition,
            "flowchart": self.flowchart,
            "official_letters": self.official_letters,
            "title_source": self.title_source,
            "source": self.source,
            "source_url": self.source_url,
            "fetched_at": self.fetched_at,
            "article_hash": self.article_hash,
            "paywalled_counts": self.paywalled_counts,
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


class Literature:
    """
    Model representing authentic legal literature / journal article.
    Strictly follows LawBank & LawData schema:
    Article title, author & affiliation, journal & issue, abstract & keywords,
    cited statutes (dual-binding), cited judgments, and PDF storage metrics.
    """
    def __init__(
        self,
        id: str,
        title: str,
        author: str,
        journal_name: str,
        subtitle: str = "",
        author_affiliation: str = "",
        pub_year: Optional[int] = None,
        pub_date: str = "",
        volume: str = "",
        issue: str = "",
        pages: str = "",
        abstract: str = "",
        abstract_en: str = "",
        keywords: Optional[List[str]] = None,
        cited_articles: Optional[List[Dict[str, str]]] = None,
        cited_judgments: Optional[List[str]] = None,
        references: Optional[List[str]] = None,
        related_literature: Optional[List[Dict[str, Any]]] = None,
        file_path: Optional[str] = None,
        file_size_bytes: int = 0,
        download_status: str = "pending",
        source_url: str = "",
        source_db: str = "lawdata"
    ):
        if not id or not str(id).strip():
            raise ValidationError("Literature ID is required.")
        if not title or not str(title).strip():
            raise ValidationError("Literature title is required.")
        if not author or not str(author).strip():
            raise ValidationError("Literature author is required.")
        if not journal_name or not str(journal_name).strip():
            raise ValidationError("Literature journal_name is required.")

        self.id = str(id).strip()
        self.title = str(title).strip()
        self.subtitle = str(subtitle or "").strip()
        self.author = str(author).strip()
        self.author_affiliation = str(author_affiliation or "").strip()
        self.journal_name = str(journal_name).strip()
        self.pub_year = int(pub_year) if pub_year is not None else None
        self.pub_date = str(pub_date or "").strip()
        self.volume = str(volume or "").strip()
        self.issue = str(issue or "").strip()
        self.pages = str(pages or "").strip()
        self.abstract = str(abstract or "").strip()
        self.abstract_en = str(abstract_en or "").strip()
        self.keywords = keywords or []
        self.cited_articles = cited_articles or []
        self.cited_judgments = cited_judgments or []
        self.references = references or []
        self.related_literature = related_literature or []
        self.file_path = file_path
        self.file_size_bytes = int(file_size_bytes or 0)
        self.download_status = download_status
        self.source_url = source_url
        self.source_db = source_db

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "subtitle": self.subtitle,
            "author": self.author,
            "author_affiliation": self.author_affiliation,
            "journal_name": self.journal_name,
            "pub_year": self.pub_year,
            "pub_date": self.pub_date,
            "volume": self.volume,
            "issue": self.issue,
            "pages": self.pages,
            "abstract": self.abstract,
            "abstract_en": self.abstract_en,
            "keywords": self.keywords,
            "cited_articles": self.cited_articles,
            "cited_judgments": self.cited_judgments,
            "references": self.references,
            "related_literature": self.related_literature,
            "file_path": self.file_path,
            "file_size_bytes": self.file_size_bytes,
            "file_size_kb": round(self.file_size_bytes / 1024, 1) if self.file_size_bytes else 0,
            "file_size_mb": round(self.file_size_bytes / (1024 * 1024), 2) if self.file_size_bytes else 0,
            "download_status": self.download_status,
            "source_url": self.source_url,
            "source_db": self.source_db
        }

