# Concepts Brief: 台灣法律檢索與校園專業文檔輔助平台 (Legal Hub)

## 1. 核心問題與目標 (Problem Statement & Goals)
使用者在行動裝置（手機）閱讀台灣法條時，常見的搜尋跳轉方式需要叫出軟體鍵盤輸入，體驗繁瑣不便；同時使用者需要定期同步常變動的台灣法規，以及從具備嚴格安全防護（Cloudflare 驗證、校園代理帳號登入、下載驗證碼）的中正大學圖書館遠端資源（AutoRPA）取得專業法律文件（法源法律網、月旦知識庫）。

本專案旨在打造一個**行動端極致便捷的法律檢索閱讀器**，並搭配**安全穩定的校園代理法律資料庫存取與輔助下載工具**。

---

## 2. 核心功能與模組設計 (Core Features & Architecture)

### A. 行動端「數字快捷直達」跳轉設計 (Mobile 0-9 Quick Dial UX)
- **痛點解決**：手機看民法或刑法等長篇法典時，叫出輸入法打字跳轉非常耗時。
- **直覺設計**：
  - 在法條瀏覽畫面底部常駐一排輕量 **數字按鈕列（`0` ~ `9`、退格 `⌫`、直達 `GO`）**。
  - 例如瀏覽民法時，依序點擊 `1` -> `8` -> `4` -> 即刻平滑滾動並高亮「第 184 條」。
  - 支援快速左右滑動章節大綱與關鍵字過濾。

### B. 台灣法規資料源與版本動態更新機制 (Dynamic Law Ingestion)
- **骨幹來源**：
  - **全國法規資料庫 (官方開放資料 Open Data)**：作為基礎骨幹（官方提供全量 XML/JSON 壓縮包與定期異動 API，最穩定、完整且無封鎖風險）。
- **變動追蹤與版本管理 (Change Detection)**：
  - 定時排程檢查官方法規最後修正日期（`LastModifiedDate`）。
  - 當法規有修正時，標註「新修條文」並保留新舊條文對照（避免舊案適用問題）。

### C. 校園代理資源存取模組 (CCU AutoRPA: LawBank & LawData)
- **目標平台**：
  1. **法源法律網 (LawBank)**: `https://www-lawbank-com-tw.autorpa.lib.ccu.edu.tw:8443/`
  2. **月旦知識庫 (LawData)**: `https://www-lawdata-com-tw.autorpa.lib.ccu.edu.tw:8443/`
- **防護環境**：中正大學 AutoRPA 遠端存取閘道（含單一簽入 SSO、Cloudflare 驗證防護）與月旦/法源下載驗證碼（CAPTCHA）。
- **技術架構：人機協同 (Human-in-the-Loop) Session 橋接器**：
  - **核心精神**：不採用容易被封鎖且脆弱的暴力破解，而是透過**本機自動化瀏覽器（Headed Browser）或本機代理服務**。
  - **流程**：
    1. 系統喚起本機瀏覽器視窗，由使用者手動輸入學校帳號並完成一次性 Cloudflare 點選與登入。
    2. 系統安全導出已通過驗證的 Session Cookie 與 Token（存在本地 `.gitignore` 的安全位置）。
    3. 下載文件遇驗證碼時：
       - 自動截取驗證碼圖片，彈出輸入框由使用者快速確認鍵入。
    4. 下載後的 PDF/全文自動標準化命名（如：`篇名_作者_期刊年份.pdf`）並自動歸檔建立全文搜尋索引。

---

## 3. GitHub 倉庫資訊
- 遠端倉庫：`https://github.com/47777777777777/legal-hub`（Private）
- 本地工作路徑：`C:/Users/harry/.gemini/antigravity-ide/scratch/legal-hub`
