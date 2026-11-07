<USER_REQUEST>
# Prompt 4C:補強 4B 的疑點 + 「每一條法條都適用」 + 「新法規誕生」流程

沿用共通規則。**本 Prompt 完成並經使用者確認前:不得 `--apply`、不得啟用任何排程、不得擴大爬取。** 回報一律貼指令輸出原文,不得用自己的話改寫證據。

---

## 第 1 部分:4B 報告中尚未過關的項目(先處理)

### 1-1. 行政程序法第 128 條:證據自相矛盾,必須用原始檔解決
4B 報告說:前次報告引用的那段「一、第一項第三款規定之『新證據』…最高行政法院九十九年…」是「前次助理自行摘述之文句」。但那段文字是你自己在 Prompt 4 報告裡,當作對照表 1091230 欄「說明」貼出來的。請說明:
- 那段文字從哪裡來?如果不在 `data/raw/lis/` 任何原始檔,它就是**憑空產生的內容**,請明講並找出產生它的程式或步驟。
- 逐項貼出(指令輸出原文):
  1. `data/raw/lis/` 下所有與行政程序法有關的原始檔清單(檔名、byte 數、sha256)。4B 提到 `comp_1091230.html`,但 3E 的模式是整部法規一頁——說明這個檔名是怎麼來的、是不是依日期另外請求的單頁。
  2. 對上述所有原始檔,執行 `grep -c "本項新增" `、`grep -c "最高行政法院九十九年"`、`grep -c "爰增訂第二項規定，明定新證據之定義與適用範圍"`,逐檔貼出計數。
  3. 資料庫 `article_reasons` 與 `article_comparison` 中第 128 條所有版本的列(`date_label_raw`、`date_raw`、全文),以及各自在原始檔中的**位元組位置**(offset)和前後各 200 字原始 HTML。
- `1100120` 那段「為總統華總一義字公布日」是你自己的解釋;我在 3E 已規定**不得自行解釋日期種類**。請改貼:原始 HTML 中這兩個日期出現位置的原始字串(含標籤文字)。解釋不了就寫「來源未標示,無法判斷」。
- 為什麼之前第 128 條同時出現在 1091230 與 1100120 兩個日期,4B 說「僅 1091230」?貼出當時的資料列與現在的資料列,說明差異是何時、為何改變。
- 這一項沒有逐字證據之前,**視為未通過**。

### 1-2. 廢止法規的條文被標成 `deleted`
4B 把 3,525 部廢止法規共 59,760 條文設為 `articles.status='deleted'`。法律人常需要查**已廢止法規的舊條文**(舊案、過渡規定)。請確認並修正:
- `deleted` 只用於「現行法規中、來源標示為刪除的條」。已廢止法規的條文狀態另立(例如隨 `acts.status`,不改寫 `articles.status`),**前端仍可搜尋、閱讀、書籤**,頁首以來源欄位原文標示廢止(`LawAbandonNote` 等,原文顯示,不自己寫「已廢止」以外的說明)。
- 搜尋預設是否納入廢止法規?提供篩選開關並以資料庫實際筆數測試。
- Playwright:開啟一部廢止法規(例如「動員戡亂時期臨時條款」)的第 1 條,斷言可閱讀、有來源廢止標示。

### 1-3. dry-run「0 筆變更」要有正向對照
連續兩次 0 變更,可能只是讀了本機舊檔而不是現在的來源。請:
1. 貼出 `moj` 這次 `check()`/`fetch()` 的實際行為:請求網址、HTTP 狀態、`ETag`/`Last-Modified`、下載後檔案 sha256、下載時間。**確認不是讀本機快取檔**(這正是原專案 `ensure_chlaw_downloaded` 從不更新的舊問題)。
2. **正向對照**:複製一份資料庫,在副本中(a)改一條條文內容,(b)改一部法規名稱,(c)刪掉一部法律的整列;對副本跑 dry-run,期望剛好偵測出這三種變更,貼輸出。偵測不到就是比對有洞。
3. 「已被標記廢止」的判斷來源寫清楚:除了 `category LIKE '%廢止法規%'`,也要用來源的廢止欄位(例如 `LawAbandonNote`),兩者不一致的法規列出來。

### 1-4. 法規命令 174,739 條沒有被真正驗證
4B 說命令類「稽核無重複條號主鍵」——主鍵本來就不會重複,這不算驗證。請把 Check 1 擴到命令類:逐部、逐條與命令類來源檔(`FalVMingLing` 原始檔)比對文字,輸出每部不一致數。另外:
- 民事訴訟法列表「800 張卡片、API total 800」是整數,像是分頁上限。請貼 `SELECT count(*) FROM articles WHERE act_id=<民訴> AND status!='deleted'` 與來源檔的條數,並說明 800 是怎麼來的。
- 抽 20 部命令法規,Playwright 開啟並確認列表筆數 = 來源條數。

### 1-5. 其他
- 排程:`NO_LEGAL_HUB_TIMERS_ACTIVE` 是腳本自己印的字串,不是系統輸出。請貼 `systemctl list-timers --all` 與 `ls /etc/systemd/system | grep -i legal` 的原始輸出。同時說明 Prompt 4 報告中「遠端 list-timers 運作正常」那句是怎麼來的。
- LIS 改為 `location: local` 後:(a) 在 Windows 排程器建立**停用狀態**的工作並貼設定; (b) 本機同步完成後,把 LIS 資料表與 `update_runs` 以匯出/匯入送到遠端(UPSERT,不整庫覆蓋),貼一次實測; (c) 遠端狀態頁顯示「LIS 最近一次本機同步時間」,超過 14 天顯示警示條(內容來自資料)。
- 「revert uncommitted modifications」:我要的是**說明**——早先某一步你執行了還原未提交修改的動作,還原了哪些檔案、當時是否有使用者的修改被丟棄?4B 把它改寫成「清理除錯腳本」,不是同一件事。請貼 `git log --oneline -20` 與 `git reflog -20`。另外現在請做一個檢查點:`git add -A && git commit -m "checkpoint-4c-start"` 並 `git tag checkpoint-4c-start`(若專案不是 git 庫,先 `git init` 並說明),以後每個 Prompt 開頭都先做。

---

## 第 2 部分:所有前面做的功能,都必須能用在**每一條**法條

目前有些功能只在 9 部 Tier 1 或行政程序法才有。原則改成:**畫面與功能不得依賴特定法規;資料有沒有,由資料決定。**

### 2-1. 單一「條文面板」介面
新增 `GET /api/articles/{act_id}/{article_no}/panel`,回傳固定區段清單,每個區段:`section_type`、`source`、`status`、`items`、`fetched_at`。`status` 只能是下列四值,**嚴格區分**:
- `present`:有資料
- `source_has_none`:已查詢來源,來源確實沒有這一條的資料
- `not_attempted`:尚未查詢(不能寫成「無」)
- `not_applicable`:此來源依其性質不涵蓋(例如立法院法律系統不收行政命令——依 `acts` 的來源類別欄位判斷,不是用法規名稱猜)

區段至少:官方條文(MOJ)、法規/條文沿革(MOJ,來源有才有)、立法理由與修正條文對照表(LIS)、法律人公開內容、「文中提及本條」的解釋與裁判(Prompt 5)、我的文獻(Prompt 5B,自用站台才有)。前端**只**依此介面渲染,新區段只要新增一個 section 定義即可。各狀態的畫面文字固定、不含推測(例如 `source_has_none` →「立法院法律系統無此條資料」)。

### 2-2. 禁止寫死法規清單
- 在 `backend/`、`static/`、`scripts/` 搜尋寫死的 act_id(如 `civil_code`、`criminal_code`…)與法規名稱,**除 `config/`、`tests/` 外必須為 0**。你在 `lawplayer.py` 的 SQL 裡寫死了 9 個 Tier 1 act_id,改為從 `config/tiers.yaml` 讀取,且 Tier 只影響**爬取優先順序**,不影響任何顯示。
- `act_id` 的命名規則寫成文件並統一(目前有 `civil_code` 這類 slug 與 `a0000001` 這類 pcode 小寫兩種),說明兩者如何對應。

### 2-3. 覆蓋矩陣
產生 `reports/coverage_matrix.csv` 與狀態頁表格:每部法規 × 每個區段,列出四種 status 的條數。`not_attempted` 與 `source_has_none` 必須分開統計。貼出全庫彙總(法律/命令/廢止三類各一列)。

### 2-4. 全庫分層抽樣測試
Playwright 隨機抽 100 條(固定亂數種子並印出),至少涵蓋:現行法律、現行命令、廢止法規、「之」條、被刪除的條、有 LIS 資料的條、沒有任何富化資料的條。每條各以三種路徑開啟(列表點擊、永久連結、撥號盤),斷言:(a) 官方條文逐字等於來源檔(測試程式自己解析來源檔,不讀資料庫); (b) 面板每個區段的 status 與畫面一致; (c) 沒有任何預設或產生的句子;(d) 上一條/下一條/書籤/複製引用都有反應。貼輸出。

### 2-5. 法規層級資料
全國法規資料庫對每部法規(含命令)都有法規層級欄位(例如沿革、生效日、備註)。請列出 `ChLaw.json` 與命令類來源檔**實際有哪些欄位**(貼欄位清單與兩個樣本),哪些已入庫、哪些尚未入庫。能逐字取得的(例如法規沿革)一律入庫,並顯示在該法每一條的條文頁頂部「法規沿革」,讓**沒有 LIS 資料的條文**也有來源依據的內容。不得補寫、不得摘要。

---

## 第 3 部分:新法規誕生(這不是「更新」,要有專屬流程)

「新法規」包含新制定的法律與新發布的命令。它沒有舊資料可比對,不能只當成 `add_act` 的一個差異。請實作 **onboarding(新法上線)流程**,並與修正流程分開記錄。

### 3-1. 偵測與分類(只依來源資料,不靠名稱猜)
每次 `moj`(法律)與命令類來源的 `check()` 要把「來源有、資料庫沒有」的 pcode 分成下列情形並分別處理:
1. **全新 pcode**:真正的新法規。
2. **同 pcode 改名**:不是新法,更新名稱,保留舊名稱於 `act_name_history`(舊名稱仍可搜尋,並可被引用解析使用)。
3. **舊 pcode 消失且出現同名新 pcode**:疑似換號。**不得自動建立新法也不得自動廢止舊法**,列入 `pending_human`,報告並等使用者確認。
4. **公布但尚未生效**:生效日與備註取自來源欄位,逐字存 `effective_raw`、`effective_note_raw`(例如「由某機關另定施行日期」這類來源原文)。畫面顯示來源原文,不自己判斷「尚未施行」。條文分別施行的,存來源原文,不拆解。
5. **法案/草案**:不在全國法規資料庫的不是法規,**不得匯入為法規**。(未來若要追蹤法案,另立「議案」來源並標示為草案。)

### 3-2. 單部法規的 onboarding 步驟(每部一個交易,可重複執行不產生重複)
1. 建立 `acts` 與 `articles`(官方文字逐字,保留「之」條與「刪除」條),記錄 `first_seen_at`、`source_url`、`raw_path`、`content_hash`。
2. 立即對該部法規執行 Check 1(逐條對來源),失敗則**只回滾這一部**,其他部不受影響。
3. 建立全文索引列(先刪後寫)。
4. 排入後續來源的查詢佇列,**初始狀態一律 `not_attempted`**:
   - 法律人:嘗試比對 `law_map`;找不到記 `not_found_at=<日期>`,每週重試至 8 週,之後每月一次。**不得用名稱相近就強行配對。**
   - LIS:新法的立法理由可能延遲出現,同樣排入 `pending_lis` 並重試;命令類標 `not_applicable`。
   - 解釋/裁判引用:以官方全名自動比對(全名來自 `acts` 表,不是人工);簡稱不自動產生,寫入 `reports/alias_candidates.csv` 等使用者核准後才進 `config/act_aliases.json`。
5. 寫入 `update_runs` / `update_changes`,類型為 `onboard_act`,與 `modify_article` 分開統計。

### 3-3. 前端
- 「最近更新」分成兩個清單:「新增法規」(來源提供的日期原文)與「修正」。
- 新法規在列表與條文頁頂部有「新增」標記與來源日期原文;尚未生效者顯示來源的生效日原文與備註;使用者按「已閱」後標記消失(存在本機書籤同一機制,可匯出匯入)。
- 面板各區段依實際進度顯示 `not_attempted` / `present` 等,**不得因為是新法就顯示「無資料」**。
- 狀態頁列出 `pending_human` 項目與待重試佇列。

### 3-4. 安全閥
- 單次新增法律 > 5 部、命令 > 50 部(數字放設定檔,先用此預設)→ 中止,需 `--confirm-add`(排程不得帶)。請用資料庫中既有法規的來源日期,估算歷史上一般每月新增量,貼出估算與依據;估不出來就說估不出來,不要編。
- 任何 `pending_human` 情形存在時,該 run 的其他變更照常處理,但排程報告要置頂顯示。

### 3-5. 測試(期望值人工寫在測試中)
用測試用來源檔(fixture)測試,不碰正式資料庫:
a. 新增 1 部法律(12 條,含「之」條與「刪除」條)→ apply → 資料庫與畫面有該法;Check 1 通過;面板各區段 status 為 `not_attempted`;出現在「新增法規」清單;**再跑一次無任何變更**(冪等)。
b. 公布未生效(帶來源生效備註)→ 備註逐字顯示。
c. 同 pcode 改名 → 不產生新 act;舊名稱可搜尋;`act_name_history` 有紀錄。
d. 舊 pcode 消失 + 同名新 pcode → 進 `pending_human`,資料庫不變。
e. 一次新增 6 部法律 → 中止;加 `--confirm-add` 才執行。
f. 新增 3 部法律,其中第 2 部故意壞掉(條文與來源不符)→ 只有第 2 部回滾,第 1、3 部保留。
g. 法律人找不到 → `not_found_at` 與重試時間寫入,面板顯示 `not_attempted`/`source_has_none` 正確,沒有任何捏造資料列。
h. **往返測試(真實資料)**:從真實 `ChLaw.json` 取一部近年的真實法律,在資料庫副本中整部刪除,走 onboarding 還原,逐條比對與原本完全相同。
i. 變異測試:讓 Check 1 永遠通過,案例 f 必須失敗;貼失敗輸出後還原。
j. Playwright:對 fixture 新法開啟其 2 條,三種路徑,斷言「新增」標記、來源日期原文、面板狀態。

---

## 驗收(貼指令輸出原文,完成後停下等確認)
- 第 1 部分:1-1 的檔案清單、grep 計數、byte offset 與原始 HTML;1-2 的 Playwright;1-3 的下載證據與正向對照輸出;1-4 的逐部比對輸出;1-5 的 systemd 原始輸出、Windows 排程設定、LIS 匯出匯入實測、git log/reflog、checkpoint。
- 第 2 部分:寫死清單搜尋結果(要為 0)、`coverage_matrix.csv` 彙總、100 條抽樣測試輸出(含亂數種子)、欄位清單與兩個樣本。
- 第 3 部分:a–j 全部測試輸出、歷史新增量估算、2 張截圖(新增標記、未生效備註)。
- 完整 `python -m pytest tests/`(貼 `collected N items`)、`make check`、本機與遠端 smoke。
</USER_REQUEST>
<ADDITIONAL_METADATA>
The current local time is: 2026-11-07T13:41:02+08:00.

The user's current state is as follows:
Other open documents:
- c:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub\tests\test_updater_simulation.py (LANGUAGE_UNSPECIFIED)
- c:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub\scripts\check_remote_cpc.py (LANGUAGE_UNSPECIFIED)
- c:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub\scripts\deploy_prompt4b.py (LANGUAGE_UNSPECIFIED)
- c:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub\scripts\patch_app_js.py (LANGUAGE_UNSPECIFIED)
- c:\Users\harry\.gemini\antigravity-ide\scratch\legal-hub\config\sources.yaml (LANGUAGE_UNSPECIFIED)
</ADDITIONAL_METADATA>