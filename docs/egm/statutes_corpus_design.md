# EGM Design Doc: 全國法規全量資料庫與即時同步架構 (All Taiwan Statutes Corpus)

## 1. 核心問題與背景 (Problem Statement & Context)
初期展示僅載入《中華民國刑法》與《中華民國民法》作為 Seed Data。為滿足專業法律研究與實務需求，系統必須能檢索並查閱**全台灣所有現行法律與命令**（超過 30,000 部法規命令與數十萬條條文），同時具備以下特點：
1. **全量涵蓋**：憲法、民法、刑法、行政法、訴訟法、商事法、勞動法、智慧財產法、行政命令及地方自治法規等。
2. **高速全文檢索**：支援模糊搜尋、條號精確跳轉、法規簡稱/全名智慧聯想。
3. **法律人規格深度擴充**：在全量法規骨幹上，無縫嫁接歷次修法理由、實務見解與官方 PDF 附檔。

---

## 2. 資料來源與同步管線 (Data Source & Ingestion Pipeline)

### 官方開放資料 (Official Open Data)
- **中文法律全集 API**：`https://law.moj.gov.tw/api/ch/law/json`
- **中文命令全集 API**：`https://law.moj.gov.tw/api/ch/order/json`
- **欄位規範**：
  - `PCode` (法規代碼，如 A0000001)
  - `LawName` (法規名稱)
  - `LawCategory` (法規類別)
  - `LawModifiedDate` (最後修正日期)
  - `LawArticles` (條文陣列：條號、條文內容)

### 儲存引擎演進 (Storage Architecture)
- 由原先的單檔 JSON 儲存庫，升級為 **SQLite 嵌入式高效能資料庫 (`data/legal_hub.db`)**：
  - `acts` 資料表：儲存 30,000+ 部法規 Metadata（PCode、名稱、類別、修正日期、沿革）。
  - `articles` 資料表：儲存數十萬條條文內容，建立 `(act_id, article_no)` 唯一索引。
  - `article_enrichments` 資料表：儲存法律人專屬深度資料（白話解析、綱要知識、歷次修正理由、實務裁判）。
  - `attachments` 資料表：儲存法規及條文之 PDF/附檔。
  - `sqlite_fts` 全文檢索模組：毫秒級全文檢索。

---

## 3. 即時與離線雙模運作 (Online / Offline Hybrid Strategy)
1. **預建核心法規庫**：預置六法全書及常用重要法規（包含刑法、民法、民事訴訟法、刑事訴訟法、行政程序法、公司法、勞基法等）。
2. **全量匯入工具 (`backend/sync_opendata.py`)**：一鍵從法務部 Open Data 同步或批次解析全量法規至本地 SQLite。
3. **即時動態抓取 Fallback (`On-Demand Ingestion`)**：若使用者搜尋極冷門或最新發布之法規，後端自動調用法務部即時 API 抓取並寫入本地資料庫。

---

## 4. 前端法規全局導覽體驗
- **頂部法規搜尋與智慧切換器 (Act Switcher with Autocomplete)**：
  - 不再只是固定的 Select 下拉選單，而是支援關鍵字輸入即時搜尋全台灣法規名稱（如輸入「勞基」自動聯想「勞動基準法」）。
- **條號直達相容**：無論切換到哪一部法規，手機端 0-9 條號直達鍵與電腦版章節大綱皆可立即定位。
