# 法規識別碼（act_id）命名規範與對應架構

## 1. 識別碼架構原則
在 Legal Hub 資料庫與系統管線中，每部法規均具備唯一的字串識別碼 `act_id`（儲存於 `acts.id`，並作為 `articles.act_id` 之外部鍵）。

系統支援並嚴格規範兩種識別碼型態：
1. **語意 Slug（Semantic Slug）**：
   - 僅供核心主要法規（如憲法、民法、刑法等常用大法規）使用，便於前端乾淨路由與人體工學檢索。
   - 命名規則：全小寫、英文字母與下劃線 `_` 組成，反映法規英文意義。
   - 範例：`constitution`、`civil_code`、`criminal_code`、`admin_procedure_act`。
   - 設定來源：統一定義於 `config/slugs.json` 與 `config/tiers.yaml`，禁止在業務程式中寫死。

2. **全國法規標準 PCode 小寫（Normalized PCode）**：
   - 全國法規資料庫所有其他法律與法規命令之標準識別碼。
   - 命名規則：法規原始 PCode（通常為 1 個英文字母加上 7 個數字，例如 `A0000001`、`B0010001`、`D0020014`）一律轉為**全小寫半形字串**（如 `a0000001`、`b0010001`、`d0020014`）。
   - 保證全局唯一且與法務部 open data 格式 1:1 可逆對應。

## 2. 雙向對應與解析規則
系統在檢索與 API 查詢時提供雙向容錯與自動解析機制：
1. **輸入 Slug 查 PCode**：
   - 查詢 `config/slugs.json` 或 `acts` 資料表，由 `acts.id = slug` 解析出對應的 `acts.pcode`。
2. **輸入 PCode 查 Slug / Act**：
   - 若法規具備 Slug，`acts.id` 為該 Slug，同時 `acts.pcode` 為大寫 PCode。
   - 若使用者或 API 傳入小寫或大寫 PCode（例如 `a0000001` 或 `A0000001`），後端 `storage.get_act()` 同時以 `id = ? OR UPPER(pcode) = UPPER(?)` 進行雙索引命中，確保兩者皆能正確開啟法規。
3. **新法上線（Onboarding）預設規則**：
   - 凡自全國法規資料庫新增之法規，`act_id` 預設直接採用其 `pcode.lower()`（如 `a0030055`）。
   - 唯有經審核且於 `config/slugs.json` 明確定義之法規，始能採用語意 Slug。

