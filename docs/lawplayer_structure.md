# LawPlayer (法律人) 網頁架構與資料格式分析文件

> 本文件記錄對 LawPlayer (lawplayer.com) 網站技術架構、前端串流傳輸協議 (Next.js RSC)、各欄位定位路徑、API 端點、反爬防護與限流表現的完整深度分析。

---

## 一、網站技術架構：Next.js App Router 與 RSC 串流

LawPlayer (lawplayer.com) 前端採用 **Next.js (App Router)** 建置，具備以下架構特性：

1. **靜態 HTML 預渲染 (SSR) 與水合 (Hydration)**：
   - 瀏覽器請求單條法條頁面（例如 `/article/6438cdc1e800e5f0b9327944`）或法規全文頁面（`/act/6437d054e800e5f0b93015aa`）時，伺服器直接回傳已包含完整 DOM 的 HTML。
   - 頁面內同時包含 Next.js Server Components 的串流腳本：
     ```html
     <script>self.__next_f.push([1,"..."])</script>
     ```
2. **RSC (React Server Components) 串流資料**：
   - 所有推播區塊以 `self.__next_f.push([1, "<escaped_string>"])` 注入。
   - 將所有串流區塊依序解碼還原後，組合成完整的 RSC 串流檔案（儲存為 `*.rsc.json`）。
   - RSC 串流內以 `ID:JSON` 格式組織各元件狀態，例如：
     - `1e:{"metadata":[["$","title","0",{"children":"民法第 2 條（適用習慣之限制）- 2026 最新全國法規資料庫｜法律人 LawPlayer"}], ...]}`
     - `46:["$","h1",null,{"className":"artw-title","children":[...]}]`
     - `4c:["$","section",null,{"className":"artw-tabs","children":[...]}]`

---

## 二、各核心欄位在頁面與資料結構中的定位路徑

為維持系統健壯性，解析器優先採用明確的語意結構與屬性標記，避免依賴易因改版失效的 CSS 亂碼類名：

| 欄位名稱 | DOM 結構定位 | RSC 串流路徑 / 標籤特徵 | 說明 / 範例 |
| :--- | :--- | :--- | :--- |
| **條標 (title)** | `h1.artw-title span.artw-title-sum` 或 `<title>` 標籤中括號 | `props.className == "artw-title-sum"` 或 `metadata.title` 中 `（...）` | 「適用習慣之限制」、「起訴之程式」 |
| **重點摘要 (summary)** | `section#w-plain p.artw-lead` (移除 `span.artw-lead-tag`) | `props.className == "artw-lead"` | 摘要本文，若無則留空 |
| **白話 Q&A (vernacular_qa)** | `div.artw-qa` (包含 `p.artw-qa-q` 與 `p.artw-qa-a`) | `props.className == "artw-qa"` | 陣列：`[{"q": "...", "a": "..."}]` |
| **深度閱讀 (deep_reading)** | `section#w-deep p` | `props.surfaceId == "law.article.deep"` 下的 section | 白話解讀與深層法律分析段落 |
| **相關函釋 (interpretations)** | `section#w-interp li.artw-interp-row` | `li` 帶 `data-doc-drawer` 或 `a[href^='/rule/']` | 包含 `org` (發文機關)、`ref` (字號)、`date` (發文字號日期)、`url` |
| **判決 (judgments)** | `section#w-precedents a[href^='/precedent/']` | `a[href^='/precedent/']` 或 `a[href^='/judgment/']` | 包含 `court` (法院/最高法院)、`ref` (字號與日期)、`url` |
| **立法沿革 (revisions)** | `section#w-evolution` 或 `section.lartf-facts li#fact-evolution` | `fact-evolution` 描述或 `w-evolution` 的各版歷史 | 包含日期、修正型態與立法沿革描述 |

---

## 三、直接可呼叫之 JSON / API 端點分析

1. **搜尋 API (`/api/search`)**：
   - 端點：`GET https://lawplayer.com/api/search?q={query}`
   - 狀態：要求 HTTP Bearer 授權（回傳 `401 Unauthorized`），供站內已登入客戶端使用，不適合作為公開爬蟲介面。
2. **Sitemap 與 RSS 靜態端點**：
   - 全站 Sitemap 索引：`https://lawplayer.com/sitemap_index.xml` (共收錄 404 個分頁 sitemap)。
   - 法規 Sitemap：`https://lawplayer.com/act-1-sitemap.xml` (收錄 12,859 部法規)。
   - 條文 Sitemap：`https://lawplayer.com/article-1-sitemap.xml` ~ `article-5-sitemap.xml`。
   - 函釋 Sitemap：`https://lawplayer.com/rule-1-sitemap.xml` ~ `rule-2-sitemap.xml`。
   - 法規 RSS：`https://lawplayer.com/rss/acts.xml`。
3. **AI 開放規範檔案**：
   - `https://lawplayer.com/llms.txt`：動態宣告台灣法規、裁判書公開引用政策，允許 AI 即時檢索引用與標示來源。
   - `https://lawplayer.com/.well-known/ai-plugin.json`：OpenAI 外掛描述規範。

---

## 四、法規全文頁面 (Act 頁) 條文列表與條號對應機制

1. **條文列表架構**：
   - 法規全文頁（如 `https://lawplayer.com/act/6437d054e800e5f0b93015aa`）**不分頁**，單頁一次渲染全部條文清單（民事訴訟法共 800 個條文節點）。
   - 每個條文節點為超連結：
     ```html
     <a href="/article/6438cf6fe800e5f0b9328b7a">
       <b>第 244 條</b> 起訴之程式
     </a>
     ```
2. **條號格式對應**：
   - LawPlayer 在條文列表中條號使用半形減號或繁體「之」，例如 `第 31-1 條`、`第 77-1 條`、`第 436-31 條`。
   - 官方全國法規資料庫 (MOJ ChLaw.json) 條號同樣使用半形減號（例如 `31-1`、`77-1`、`436-31`）。
   - 正規化規則：以正則表達式 `第\s*(\d+(?:[-－之]\d+)?)\s*條` 擷取，將全形 `－` 或中文字 `之` 轉換為半形 `-`，即可與全國法規資料庫 800 條達成 **100% 精確對齊**。

---

## 五、Robots.txt、登入與限流表現分析

1. **robots.txt 規範**：
   - 站方開放一般頁面抓取 (`Allow: /`)，但明確禁止存取內部 API 端點（如 `Disallow: /api/`、`Disallow: /read-api/` 等）以及附帶 Next.js RSC 查詢字串之請求（`Disallow: /*?_rsc=`）。
   - 對各大爬蟲及通用 User-Agent 宣告 `Crawl-delay: 1`。
2. **登入與 Cookie**：
   - 條文原文、條標、白話摘要、白話 Q&A、相關函釋清單、引用裁判書清單皆為**公開 SSR 內容**，無需登入、無需帶 Cookie。
   - 僅「共同筆記」(notes) 及部分會員收藏功能需登入。
3. **雲端與機房限流 (Cloudflare 403)**：
   - 法律人使用 Cloudflare 防護。經實測：
     - 本機開發機（家用/商用寬頻）以一般瀏覽器 Header（`User-Agent`）請求均為 HTTP 200，無驗證碼阻擋。
     - 遠端雲端伺服器（機房 IP `161.33.166.144`）之請求會被 Cloudflare 判定為 Datacenter IP 攔截（回傳 HTTP 403 Forbidden）。
   - **採集架構策略**：爬取與解析任務須在本機或代理節點完成，再透過內部資料管道部署同步至遠端伺服器資料庫。

---

## 六、真實瀏覽器探測：流程圖與立法理由之付費牆 (Paywall) 邊界實測

針對使用者提出之「法律人頁面上的流程圖」與「立法理由」，透過真實無狀態瀏覽器（Playwright，未登入乾淨無 Cookie 環境，點擊間隔 $\ge 2$ 秒，完整錄製 HAR 網路封包與 DOM 結構）進行深度探測。

### 1. 探測目標與封包紀錄
- **民法第 2 條**：`https://lawplayer.com/article/6438cdc1e800e5f0b9327944`
  - HAR 封包紀錄：`data/raw/lawplayer/har/civil_code_art_2.har`（76 個 HTTP 請求，大小 5.1 MB）
  - 畫面截圖：`civil_code_art_2_tab_關鍵知識.png`、`civil_code_art_2_tab_內容連結.png`、`civil_code_art_2_tab_立法理由.png`
- **民事訴訟法第 244 條**：`https://lawplayer.com/article/6438cf6fe800e5f0b9328b7a`
  - HAR 封包紀錄：`data/raw/lawplayer/har/cpc_art_244.har`（78 個 HTTP 請求，大小 5.1 MB）
  - 畫面截圖：`cpc_art_244_tab_關鍵知識.png`、`cpc_art_244_tab_內容連結.png`、`cpc_art_244_tab_立法理由.png`
- **請求彙整與 DOM 結構摘要**：`data/raw/lawplayer/har/requests_summary.json`

### 2. 「立法理由」實測結果：確認受會員付費牆 (Paywall) 鎖定
- 在真實未登入瀏覽器中，點擊「立法理由」分頁，DOM 渲染出的真實內容如下：
  - **民法第 2 條**：
    ```text
    本條有 1 段立法理由。
    立法理由 也在牆內
    在上方解鎖 ↑
    ```
  - **民事訴訟法第 244 條**：
    ```text
    本條有 4 段立法理由。
    立法理由 也在牆內
    在上方解鎖 ↑
    ```
- **結構化資料層面**：法律人後端在 Next.js RSC 串流中僅輸出付費提示文字與段落數事實陳述，未將完整的立法理由文字下發至公開前端。法律人將立法理由全文列為加值會員付費內容。

### 3. 「流程圖」實測結果：公開頁面無向量圖形或結構化資料
- **DOM 節點分析**：
  - 檢視 `cpc_art_244` 與 `civil_code_art_2` 的完整 DOM 樹狀結構，完全不存在寬高大於 $80 \times 60$ 的 `<svg>`、`<canvas>`、或流程圖專屬之 `<img>`。
  - 切換「關鍵知識」、「內容連結」、「立法理由」等分頁時，前端未發出任何背景 XHR/Fetch 去向伺服器請求額外的流程圖 JSON 或向量資產（所有可讀內容皆在首包 SSR/RSC 內）。
- **付費牆機制**：法律人的互動流程圖係針對已登入之付費會員開放之專屬模組；在公開未授權訪客的 HTML 與 RSC 串流中，無任何流程圖之圖片路徑、Mermaid 語法或結構化節點。

### 4. 遵守系統安全與改動紀律
- 依據共通規則第一條「禁止手寫/推測/編造任何法律內容」與第二條防護紀律，**嚴禁在前端或資料庫偽造通用流程圖**，亦嚴禁嘗試繞過付費牆或未經授權逆向爬取會員專屬資料。
- 未經公開抓取之條文（如民訴第 2 條），明確顯示「此條尚無立法理由資料」與「此條尚無實務見解資料」，維持 100% 真實與零造假。
