# EGM Design Doc: 全國法規全量資料庫與即時同步架構 (All Taiwan Statutes Corpus)

## 1. 核心問題與背景 (Problem Statement & Context)
初期展示僅載入《中華民國刑法》與《中華民國民法》作為 Seed Data。為滿足專業法律研究與實務需求，系統必須能檢索並查閱**全台灣所有現行法律與命令**（超過 30,000 部法規命令與數十萬條條文），同時具備以下特點：
1. **全量涵蓋**：憲法、民法、刑法、行政法、訴訟法、商事法、勞動法、智慧財產法、行政命令及地方自治法規等。
2. **高速全文檢索**：支援中文無空格切詞檢索、條號精確跳轉、法規簡稱/全名智慧聯想。
3. **法律人規格深度擴充**：在全量法規骨幹上，無縫嫁接歷次修法理由、實務見解與官方 PDF 附檔。

---

## 2. 資料庫架構與 DDL 規範 (SQLite Database Schema & DDL)

### 儲存引擎標準：SQLite 3.34+ 嵌入式資料庫 (`data/legal_hub.db`)

```sql
-- 1. 法規基本資料表 (支援 Slug 與 MOJ PCode 雙軌索引)
CREATE TABLE IF NOT EXISTS acts (
    id TEXT PRIMARY KEY,                       -- 如 'criminal_code' 或 'C0000001'
    pcode TEXT UNIQUE,                         -- 法務部官方 PCode (如 C0000001)
    name TEXT NOT NULL,                        -- 法規名稱 (如 '中華民國刑法')
    name_en TEXT,                              -- 英文法規名稱
    category TEXT,                             -- 主管部會類別 (如 '行政 > 法務部 > 檢察目')
    last_modified TEXT,                        -- 最後修正日期
    org_reform_notice TEXT,                    -- 機關改造沿革提示
    history_json TEXT DEFAULT '[]',            -- 沿革歷程 JSON
    legislative_process_json TEXT DEFAULT '[]',-- 立法歷程 JSON
    chapters_json TEXT DEFAULT '[]',           -- 編章節樹狀結構 JSON
    is_enriched INTEGER DEFAULT 0,             -- 是否包含法律人深度研析標籤 (1=是, 0=否)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_acts_name ON acts(name);
CREATE INDEX IF NOT EXISTS idx_acts_pcode ON acts(pcode);

-- 2. 法規條文主檔表
CREATE TABLE IF NOT EXISTS articles (
    act_id TEXT NOT NULL,                      -- 外鍵關聯 acts(id)
    article_no TEXT NOT NULL,                  -- 正規化條號 (如 '1', '185-3')
    title TEXT,                                -- 條文罪名或簡旨 (如 '不能安全駕駛罪')
    chapter TEXT,                              -- 所屬編章節
    content TEXT NOT NULL,                     -- 條文全文 (項款目)
    PRIMARY KEY (act_id, article_no),
    FOREIGN KEY (act_id) REFERENCES acts(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_articles_lookup ON articles(act_id, article_no);

-- 3. 法律人深度研析與歷次修法理由表 (獨立分離，防止同步時被官方純條文覆蓋)
CREATE TABLE IF NOT EXISTS article_enrichments (
    act_id TEXT NOT NULL,
    article_no TEXT NOT NULL,
    summary TEXT,                              -- 重點摘要 (Callout box)
    reading_time TEXT DEFAULT '3 分鐘',         -- 預估閱讀時間
    vernacular_qa_json TEXT DEFAULT '[]',      -- 白話解讀與 Q&A JSON
    elements_json TEXT DEFAULT '[]',           -- 構成要件拆解 JSON
    key_issues_json TEXT DEFAULT '[]',         -- 核心爭點速覽 JSON
    legislative_reasons TEXT,                  -- 最新立法理由
    amendment_history_json TEXT DEFAULT '[]',  -- 歷次修正理由及新舊條文對照 JSON
    practical_insights_json TEXT DEFAULT '[]', -- 實務裁判與判例見解 JSON
    lawplayer_link TEXT,                       -- 外部法律人直達超連結
    related_articles_json TEXT DEFAULT '[]',   -- 跨法規關聯條文 JSON
    PRIMARY KEY (act_id, article_no),
    FOREIGN KEY (act_id, article_no) REFERENCES articles(act_id, article_no) ON DELETE CASCADE
);

-- 4. 法規及條文法定附檔表
CREATE TABLE IF NOT EXISTS attachments (
    id TEXT PRIMARY KEY,
    act_id TEXT NOT NULL,
    article_no TEXT,                           -- 若為全法通用附檔則為 NULL
    title TEXT NOT NULL,
    file_type TEXT DEFAULT 'PDF',
    url TEXT NOT NULL,
    description TEXT,
    FOREIGN KEY (act_id) REFERENCES acts(id) ON DELETE CASCADE
);

-- 5. 中文全文檢索 FTS5 虛擬表 (採用 trigram 切詞，支援繁體中文無空格精確全文搜尋)
CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
    act_id UNINDEXED,
    article_no UNINDEXED,
    title,
    content,
    tokenize='trigram'
);
```

---

## 3. 全國法規資料庫 (MOJ Open Data) 格式轉化與同步規範

1. **條號正規化 (Normalization)**：
   - MOJ 原始資料常標示為 `第 1 條`、`第 185-3 條`、`第 一百八十五條之三 條`。
   - 解析規則：以正則表達式萃取核心數值 `r"^第\s*([0-9]+(?:-[0-9]+)?)\s*條$"`，統一歸一為 `185-3`、`184`、`1`，確保前後端路由及直達鍵盤能精確命中。
2. **編章節分離 (ArticleType 區分)**：
   - MOJ Open Data 中 `ArticleType: "C"` 代表編、章、節標題，自動聚合入 `acts.chapters_json`。
   - `ArticleType: "A"` 代表實質法條，寫入 `articles` 資料表。
3. **無損更新機制 (Non-Destructive Upsert)**：
   - 全量同步時，使用 `INSERT ... ON CONFLICT(act_id, article_no) DO UPDATE SET content=excluded.content, title=excluded.title`。
   - **嚴禁覆寫** `article_enrichments` 表中的法律人註解、白話問答與實務裁判。

---

## 4. 檢索與前端雙模相容
- 支援以 `id` (例如 `criminal_code`) 或 `pcode` (例如 `C0000001`) 或 `name` (例如 `中華民國刑法`) 查詢法規。
- 頂部導覽列提供全國法規即時聯想搜尋框，使用者輸入關鍵字可即時列出全台各部會法規並切換載入。
