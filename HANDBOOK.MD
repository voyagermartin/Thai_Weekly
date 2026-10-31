# Thai_Weekly (泰語學習週報自動化系統) 專案協作手冊

> **專案版本**：v3.3 (Web-First 雙軌驅動・即時 AI 詞典與個人化演進版) ｜ **更新日期**：2026-10-31  
> **線上站點**：[Thai_Weekly GitHub Pages](https://voyagermartin.github.io/Thai_Weekly/) ｜ **維護者**：Martin × Antigravity × Gemini API  

---

## 1. 核心願景與架構準則

### 1.1 願景與戰略（Web-First, Mail-Light）
* **全功能網站化**：教學互動、說文解字、語音發音、自測遮蔽與即時 AI 構詞剖析，100% 收斂於網站端完成。全站採**泰皇暗夜紫金風（Dark Editorial Magazine UI）**。
* **郵件輕量化**：每週六 09:00 由 GAS 原生發送極簡提醒信（專屬問候＋一句導讀＋直達按鈕），免除排版負擔與擋信風險。
* **🚨 開發除錯鐵律**：**非必要嚴禁主動開啟瀏覽器測試**。日常功能排查、邏輯驗證與修復一律透過代碼審查、單元測試或終端指令（curl/CLI）完成，杜絕資源耗損。

### 1.2 系統架構流程圖 (Sheet-as-a-CMS & Realtime AI)

```mermaid
flowchart TD
    subgraph 自動出刊與排程
        Cron["時間排程 (週六 09:00)"] --> GAS["GAS weeklyAutoPublish()"]
        GAS --> Gemini["Gemini 3.5 API 出刊 (繁中 JSON)"]
        Gemini --> Sheet["寫入 Google Sheet 四大分頁"]
        Sheet --> Mail["MailApp 一對一寄送極簡提醒信"]
    end

    subgraph 前端即時互動 (GitHub Pages)
        Reader["讀者造訪 index.html / lesson.html"]
        GViz["GViz API (&headers=1) 讀取試算表"] --> Reader
        Reader --> Anatomy["即時說文解字查詢 (action: analyze_word)"]
        Anatomy --> WebApp["GAS Web App (ANYONE_ANONYMOUS)"]
        WebApp --> GeminiLive["Gemini 即時構詞剖析"]
        GeminiLive --> AnatomyUI["動態展開紫金卡片與 TTS 發音"]
    end
    Mail -.-> Reader
```

---

## 2. 雲端資料庫規格 (Database Specifications)

* **試算表名稱**：`Thai_Weekly_DB（泰語學習週報資料庫）`
* **試算表 ID**：[`1DvxPjzNRlTRSMSXr6eaktU2dBQZSS9oWadNfT3_ZUTM`](https://docs.google.com/spreadsheets/d/1DvxPjzNRlTRSMSXr6eaktU2dBQZSS9oWadNfT3_ZUTM/edit)（權限：公開檢視，零 CORS 限制）
* **GViz 查詢規範**：前端請求必須附帶 `&headers=1`，確保第 1 列為標頭：  
  `https://docs.google.com/spreadsheets/d/1DvxPjzNRlTRSMSXr6eaktU2dBQZSS9oWadNfT3_ZUTM/gviz/tq?tqx=out:json&sheet={工作表名稱}&headers=1`

### 2.1 四大工作表欄位定義
| 工作表 | 欄位結構與說明 |
| :--- | :--- |
| **`Issues`** | `issue_code` ｜ `year` ｜ `week` ｜ `publish_date` ｜ `status` (published/upcoming) ｜ `title` ｜ `subtitle_1` ｜ `subtitle_2` ｜ `read_time` ｜ `highlights` ｜ `culture_title` ｜ `culture_body_html` ｜ `culture_memo_html` ｜ `email_subject` ｜ `email_intro_html` ｜ `email_highlights_html` |
| **`Vocab`** (7欄) | `issue_code` ｜ `type` (core/culture) ｜ `thai` ｜ `phonetic` ｜ `meaning` ｜ `breakdown_json` (詞素字根拆解 JSON 陣列；單字根或外來語回傳 `[]`) ｜ `extensions_json` (延伸派生詞 JSON 陣列) |
| **`Sentences`** | `issue_code` ｜ `order` (1~5) ｜ `thai` ｜ `phonetic` ｜ `meaning` |
| **`Grammar`** | `issue_code` ｜ `point_num` (1~2) ｜ `title` ｜ `explanation_html` ｜ `examples_json` (`[{"thai": "...", "phonetic": "...", "meaning": "..."}]`) |

---

## 3. 前端動態渲染系統架構 (Frontend Dynamic CMS)

### 3.1 專案目錄結構
```text
Thai_Weekly/
├── index.html                  # 站點首頁（Spotlight Hero、即時構詞詞典、期數搜尋、歷史手風琴）
├── lesson.html                 # 動態課程頁（?issue=YYwWW，含說文解字抽屜、即時查詢、TTS、遮蔽自測）
├── 26w41.html ~ 26w44.html     # 歷史相容自動跳轉頁（導向 lesson.html?issue=26wXX）
├── gas/
│   ├── appsscript.json         # Apps Script 清單（宣告 ANYONE_ANONYMOUS 存取權限）
│   └── Code.gs                 # 後端中樞腳本（出刊、寄信、即時單字分析、歷史回填）
└── HANDBOOK.MD                 # 本手冊（架構規範與開發標準）
```

### 3.2 視覺與互動技術規範
* **色彩與排版**：底色 `--bg-base: #0d0814`、卡片 `--bg-card: #231738`、金箔標註 `--accent-gold: #f59e0b`、泰文字級 `--text-thai: #fde047`。核心單字 34px、情境句 25px、內文 17.5px。
* **說文解字抽屜 (Word Anatomy Drawer)**：
  - **動態辨識按鈕**：僅在 `breakdown` 有值時於卡片右上角注入 `.btn-anatomy-toggle`，未展開時卡片維持等高。
  - **上下層次卡片**：拆解積木（`.anatomy-item`）採獨立圓角卡片，上方 Header Flex 整合泰文、音標與 🔊 迷你發音，下方 Body 為釋義，元件間以置中金色 `+` 串接。
  - **泰文折行防護**：套用 `white-space: nowrap; word-break: keep-all;`，徹底根絕泰文母音符號拆裂至下一行。
* **即時說文解字詞典 (On-the-fly Anatomy Tool)**：
  - 首頁與課程頁同步掛載，雙重傳輸容錯（預設 `POST`，異常自動切換為 `GET` 備援）。
  - 全域輔助提升：`escapeQuote` 與 `safeParseJsonArray` 位於腳本最頂層，確保防護跳脫字元。
* **雙引擎語音播放 (TTS)**：
  - 第一引擎 Google TTS 串流，備援 Web Speech API 原生語音 (`th-TH`)。
  - 鎖定 `enforceRate()` 與 `audio.defaultPlaybackRate`，確保 0.75x 與 1.0x 顯著區別，並以 `localStorage` 持久化記憶讀者速率偏好。

---

## 4. Google Apps Script 後端中樞與安全防禦

* **Script ID**：[`1fJ_JIB0aET_pLwDOJasv47YzSBn3xk7NhW3h96919NRd2opJpq-VOOmA`](https://script.google.com/home/projects/1fJ_JIB0aET_pLwDOJasv47YzSBn3xk7NhW3h96919NRd2opJpq-VOOmA/edit)
* **Web App 端點**：`https://script.google.com/macros/s/AKfycbxiY6t8K_BmB2oRWhbi7UZCHpN1Blmd1BEH8APe3PW6gXCKX2XcNYHcDZhZfMZtifi4/exec`（部署權限：`ANYONE_ANONYMOUS`，免登入匿名跨域連線）
* **零暴露 API 金鑰防禦**：全專案 0 硬編碼金鑰。金鑰保存在雲端 `ScriptProperties`，透過試算表上方「🚀 週報自動化控制台」選單互動式寫入。
* **核心後端函式**：
  - `weeklyAutoPublish()`：每週六 09:00 時間驅動排程觸發，呼叫 Gemini 出刊寫入四大分頁並寄信。
  - `analyzeSingleWord(word)`：支援 `action: "analyze_word"`，呼叫 Gemini 3.5 剖析構詞，支援複合詞拆解與外來語/單字根防呆排除。
  - `backfillAnatomyForIssue(issueCode)`：零手動批次自動回填歷史期數之單字拆解與派生詞至 F、G 欄。
* **一對一寄信清單 (MailApp.sendEmail)**：
  - `voyager.martin@gmail.com` ➔ `早安 Martin！`
  - `anniechen0209@gmail.com` ➔ `早安 Annie！`
  - `tienzitw@yahoo.com.tw` ➔ `早安 昌哥！`

---

## 5. 里程碑記錄 (Milestones Summary)

- [x] **v1.0 ~ v2.0**：泰皇紫金雜誌風、34px 沉浸式字級、雙引擎語音播放、文化專題發音。
- [x] **v3.0**：重大架構升級 Sheet-as-a-CMS，建立 `Thai_Weekly_DB` 與動態 `lesson.html` / `index.html`，Git 歷史金鑰淨化。
- [x] **v3.1**：發布 26w44；修復 GViz `&headers=1` 標頭缺陷；解決 HTML5 Audio 降速重置問題；實現語音速率本地記憶。
- [x] **v3.2**：擴充 `Vocab` 7 欄架構，建立複合詞字根拆解與延伸詞機制；實作折疊抽屜與解決泰文折行斷字。
- [x] **v3.3**：全站雙端（首頁與課程頁）上線「即時說文解字 AI 詞典」；廢棄舊版 GitHub Actions 出刊排程；確立 Web-First 演進架構。

---

## 6. 下階段開發演進展望 (Next Phase Roadmap)

1. **學習歷程本地持久化**：`localStorage` 記錄已讀期數徽章與「核心單字收藏本 (Saved Vocab)」。
2. **單元測驗模式增強**：獨立切換遮蔽「泰文字/音標/釋義」；課程底部整合 3 題快速自測。
3. **多媒體內容延伸**：評估 Sheet 支援短影片（YouTube Shorts）或情境音檔直連。
4. **Web-First 個人化學習與訂閱演進架構 (Personalized Learning Hub)**：
   * **第一階段：前端本機偏好抽屜 (Local Preferences Drawer)**
     - 免登入架構：右上角增設「👤 學習偏好」按鈕（`localStorage` 記憶）。
     - 讀者自訂：暱稱、性別（網頁例句尾音動態切換 `ครับ / ค่ะ`）、興趣標籤（馬拉松、商務、咖啡等）。
     - 課程頁動態載入：`lesson.html` 依據標籤即時掛載「🎯 專屬興趣加強包（3 個單字＋1 實戰句）」，不污染試算表。
   * **第二階段：VIP 訂閱制與雲端 Profile 聯動 (Cloud Sync & Membership)**
     - 試算表增設 `Subscribers` 分頁（`email | nickname | gender | interest_tags | status`）。
     - 郵件提醒按鈕附帶個人識別碼（`lesson.html?issue=YYwWW&uid={user_id}`），一鍵直達載入雲端設定專屬課堂。
