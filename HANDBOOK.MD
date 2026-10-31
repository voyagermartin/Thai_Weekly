# Thai_Weekly (泰語學習週報自動化發布系統) 專案協作手冊

> **專案版本**：v3.3 (說文解字全端雙核驅動・即時 AI 詞典與個人化演進版)  
> **最後更新日期**：2026-10-31  
> **維護者**：Martin × Antigravity (Anti) × Gemini API  
> **線上站點**：[Thai_Weekly GitHub Pages](https://voyagermartin.github.io/Thai_Weekly/)

---

## 1. 專案願景與協作架構 (Vision & Pipeline)

### 1.1 願景 (Vision)
打造一個**全自動、零手動維護、支援原地標準語音播放與卡片互動自測**的現代化泰語自主學習網站。全站採用**泰國皇室紫金風（Dark Editorial Magazine UI）**，支援雙引擎 TTS 語音發音與沉浸式大字級排版。

### 1.2 結構化資料庫驅動架構 (Sheet-as-a-CMS & Realtime AI)

在 v3.0～v3.3 重構中，系統徹底邁向 **「Google Sheet-as-a-CMS 驅動 ＋ Realtime Gemini AI」** 雙軌架構，全面解決以下痛點：
- **消滅檔案搬移失敗與 Git Push 依賴**：每週出刊只需將結構化資料寫入 Google Sheet，前端網頁即時動態渲染出最新期數，徹底免去每週生成靜態 HTML 與 Git Commit Push 的維護負擔。
- **根絕真人確認卡與流程攔截**：採用 Google Apps Script 原生 `MailApp.sendEmail`，享受 Google 帳戶每日原生發信額度，無真人確認卡阻擋。
- **根除 404 找不到網頁時序爭執**：資料一入庫，前端 `lesson.html?issue=YYwWW` 隨即生效，信件中的閱讀按鈕點擊必有網頁！
- **雲端安全零暴露防禦**：API 金鑰由 Google Apps Script 雲端原生指令碼屬性庫 (`ScriptProperties`) 加密持久化，Git 倉庫與本機原始碼達成 100% 零硬編碼洩漏風險。
- **全站雙端即時 AI 構詞剖析**：首頁與課程頁皆具備即時泰語說文解字查詢工具，由 GAS Web App 端點無縫呼叫 Gemini 3.5 AI，即刻解析任意泰語複合詞素並動態渲染紫金卡片。

### 1.3 協作開發與除錯驗證準則 (Development & Testing Guidelines)
* **非必要嚴禁開啟瀏覽器做測試**：為確保開發效率、維持作業環境清爽與降低系統資源消耗，日常功能排查、邏輯驗證與修復應優先透過靜態代碼審查、輕量單元測試或本機終端指令進行，**非必要嚴禁主動啟動瀏覽器（Browser Agent / Headless Window）進行測試**。

```mermaid
flowchart TD
    A["時間驅動排程 (每週六 09:00 台北時間)"] --> B["Google Apps Script 執行 weeklyAutoPublish()"]
    B --> C["從 ScriptProperties 讀取 GEMINI_API_KEY"]
    C --> D["呼叫 Google Gemini API 產出教材 JSON
(含複合詞說文解字 breakdown & extensions)"]
    D --> E["SpreadsheetApp 寫入 Google Sheet 四大分頁
(Issues, Vocab 7欄, Sentences, Grammar)"]
    E --> F["資料入庫即刻生效！前端即時可用"]
    E --> G["MailApp.sendEmail 獨立發送 3 封一對一專屬問候信"]
    
    subgraph 前端即時讀取與互動 (GitHub Pages)
        H["讀者造訪 index.html 或 lesson.html?issue=YYwWW"]
        H --> I["Google Visualization JSON API (GViz &headers=1) 即時查詢試算表"]
        I --> J["動態渲染紫金首頁 Hero、手風琴歸檔或課程四大專欄"]
        K["讀者於搜尋框貼上任意泰文字串"] --> L["呼叫 GAS Web App 端點 (action: analyze_word)"]
        L --> M["Gemini 3.5 即時構詞剖析 (breakdown + extensions)"]
        M --> N["動態展開說文解字紫金卡片與雙引擎 TTS 語音發音"]
    end

    G --> H
    
    style A fill:#1e293b,stroke:#38bdf8,color:#fff
    style B fill:#1e293b,stroke:#a855f7,color:#fff
    style C fill:#0f172a,stroke:#f59e0b,color:#fff
    style D fill:#0f172a,stroke:#38bdf8,color:#fff
    style E fill:#047857,stroke:#10b981,color:#fff
    style F fill:#0284c7,stroke:#f59e0b,color:#fff
    style G fill:#b45309,stroke:#f59e0b,color:#fff
    style H fill:#1e293b,stroke:#fde047,color:#fff
    style I fill:#1e293b,stroke:#38bdf8,color:#fff
    style J fill:#231738,stroke:#f59e0b,color:#fff
    style K fill:#231738,stroke:#f59e0b,color:#fff
    style L fill:#1e293b,stroke:#a855f7,color:#fff
    style M fill:#0f172a,stroke:#38bdf8,color:#fff
    style N fill:#231738,stroke:#fde047,color:#fff
```

---

## 2. 雲端資料庫規格 (Database Specifications)

* **目標資料夾**：`泰文小短篇` (Folder ID: `1xTWvfaAEIqzHFpDKtG7ipdMBZf8PYbBA`)
* **試算表名稱**：`Thai_Weekly_DB（泰語學習週報資料庫）`
* **試算表 ID**：[`1DvxPjzNRlTRSMSXr6eaktU2dBQZSS9oWadNfT3_ZUTM`](https://docs.google.com/spreadsheets/d/1DvxPjzNRlTRSMSXr6eaktU2dBQZSS9oWadNfT3_ZUTM/edit)
* **存取權限**：公開（知道連結的任何人均可檢視，無需 API Key，零 CORS 限制）
* **線上編輯網址**：[開啟 Google Sheet 資料庫](https://docs.google.com/spreadsheets/d/1DvxPjzNRlTRSMSXr6eaktU2dBQZSS9oWadNfT3_ZUTM/edit)

### 2.1 四大工作表 (Tabs) 結構與欄位定義

1. **`Issues`（期數主表）**
   - `issue_code` (如 26w44) ｜ `year` ｜ `week` ｜ `publish_date` ｜ `status` (published / upcoming) ｜ `title` ｜ `subtitle_1` ｜ `subtitle_2` ｜ `read_time` ｜ `highlights` ｜ `culture_title` ｜ `culture_body_html` ｜ `culture_memo_html` ｜ `email_subject` ｜ `email_intro_html` ｜ `email_highlights_html`
2. **`Vocab`（單字庫，擴充為 7 欄架構）**
   - 欄位 A：`issue_code` (期數編號，如 26w44)
   - 欄位 B：`type` (`core` 核心字 / `culture` 文化專題單字)
   - 欄位 C：`thai` (泰文字串)
   - 欄位 D：`phonetic` (羅馬拼音音標)
   - 欄位 E：`meaning` (繁體中文釋義，含詞性如 `[名詞] 止痛藥`)
   - 欄位 F：`breakdown_json` (說文解字詞素拆解 JSON 陣列，如：`[{"thai": "ยา", "phonetic": "yaa", "meaning": "藥"}, {"thai": "แก้", "phonetic": "kâe", "meaning": "解/止"}, {"thai": "ปวด", "phonetic": "pùat", "meaning": "痛"}]`；單一字根詞或外來語回傳 `[]`)
   - 欄位 G：`extensions_json` (延伸衍生詞 JSON 陣列，如：`[{"thai": "ยาแก้ไอ", "phonetic": "yaa kâe ai", "meaning": "止咳藥"}]`)
3. **`Sentences`（情境句型庫）**
   - `issue_code` ｜ `order` (1~5) ｜ `thai` ｜ `phonetic` ｜ `meaning`
4. **`Grammar`（語法解析庫）**
   - `issue_code` ｜ `point_num` (1~2) ｜ `title` ｜ `explanation_html` ｜ `examples_json` (例句陣列 JSON：`[{"thai": "...", "phonetic": "...", "meaning": "..."}]`)

### 2.2 GViz API 前端無密鑰查詢規範
前端採用 Google Visualization API (GViz) 直接查詢試算表，零 CORS 限制、無需任何前端 API Key（**務必附帶 `&headers=1`**，強制宣告第 1 列為標題列，避免 GViz 啟發式演算法將多筆字串資料列誤判合併至標頭）：
`https://docs.google.com/spreadsheets/d/1DvxPjzNRlTRSMSXr6eaktU2dBQZSS9oWadNfT3_ZUTM/gviz/tq?tqx=out:json&sheet={工作表名稱}&headers=1`

---

## 3. 前端動態渲染系統架構 (Frontend Dynamic CMS)

```text
Thai_Weekly/
├── .clasp.json                 # Google Apps Script 本地專案綁定配置檔
├── index.html                  # 站點首頁（Spotlight Hero、即時構詞詞典、期數搜尋、近期特輯與歷史手風琴）
├── lesson.html                 # 動態課程頁（依 ?issue=YYwWW 參數即時載入，含說文解字抽屜、即時查詢框、TTS 與遮蔽自測）
├── 26w41.html                  # 歷史相容跳轉頁（內嵌自動導向 lesson.html?issue=26w41）
├── 26w42.html                  # 歷史相容跳轉頁（內嵌自動導向 lesson.html?issue=26w42）
├── 26w43.html                  # 歷史相容跳轉頁（內嵌自動導向 lesson.html?issue=26w43）
├── 26w44.html                  # 歷史相容跳轉頁（內嵌自動導向 lesson.html?issue=26w44）
├── favicon.svg                 # 專屬深邃曜石黑 × 科技藍漸層泰語學習 App 圖標
├── templates/
│   └── lesson_template.html    # 紫金版面設計基準模板（供動態骨架參考）
├── gas/
│   ├── appsscript.json         # Apps Script 專案資訊清單（設定 ANYONE_ANONYMOUS 權限）
│   └── Code.gs                 # 綁定 Google Apps Script 原生自動化腳本（含即時剖析與歷史回填函式）
├── scripts/
│   ├── Thai_Weekly_DB.xlsx     # 結構化資料庫本地工作簿快照
│   ├── create_sheet_from_xlsx.py # 試算表轉換建立工具
│   ├── deploy_gas.py           # Google Apps Script 遠端程式碼部署工具（原地更新部署）
│   ├── parse_lessons.py        # 歷史 HTML 解析工具
│   └── db_config.json          # 資料庫 ID 與端點快照設定檔
└── HANDBOOK.MD                 # 本專案協作手冊（最高指導指引）
```

### 3.1 視覺與技術規範 (Design & Interaction System)
* **配色系統**：
  * 背景基底：`--bg-base: #0d0814` (暹羅暗夜紫底)
  * 卡片表層：`--bg-card: #231738` (帝王紫卡片)
  * 金箔高光：`--accent-gold: #f59e0b` (泰皇金箔金)
  * 泰文專屬：`--text-thai: #fde047` (黑底金字大字體)
* **字級與容器**：
  * 桌機容器寬度：1160px（大螢幕自動擴展至 1240px）。
  * 核心單字 34px、情境例句 25px、內文 17.5px。
* **安全標頭**：`<meta name="referrer" content="no-referrer">`。
* **說文解字・詞彙拆解抽屜 (Word Anatomy Drawer)**：
  * **按鈕動態注入**：前端渲染單字卡片時自動判斷 `item.breakdown && item.breakdown.length > 0`，有拆解資料才注入切換按鈕 (`.btn-anatomy-toggle`)，維持卡片初始整齊等高。
  * **上下層次卡片**：拆解積木採上下層次結構（`.anatomy-item`），頂部 Header Flex 整合泰文大字、音標與 🔊 迷你發音按鈕，下方 Body 呈現中文釋義與金色詞性標籤，元件間以置中淡金 `+` 串接。
  * **泰文字不折行防護**：針對拆解泰文字加上 `white-space: nowrap; word-break: keep-all;`，徹底根絕泰文母音符號拆裂至次行之缺陷。
  * **延伸派生詞網**：縱向卡片條列 (`.extension-card`)，同樣具備獨立 🔊 語音發音與遮蔽自測相容機制。
* **全站雙端即時說文解字詞典 (On-the-fly Word Anatomy Tool)**：
  * 課程頁 [`lesson.html`](file:///f:/Projects/Thai_Weekly/lesson.html) 單字庫頂部與首頁 [`index.html`](file:///f:/Projects/Thai_Weekly/index.html) Spotlight Hero 下方皆掛載即時構詞查詢框。
  * **雙重傳輸容錯**：`submitLiveAnatomy()` 預設使用 `POST` 呼叫 Web App，遇網路異常自動切換為帶參數之 `GET` 備援請求。
  * **全域輔助提升**：`escapeQuote`（跳脫單引號防範 onclick 中斷）與 `safeParseJsonArray` 提升至腳本頂層作用域。
* **雙引擎語音播放系統**：
  * 第一引擎：Google TTS 原地串流 (`audio/mpeg`)。
  * 第二引擎：自動備援 Web Speech API 原生合成語音 (`th-TH`)。
  * **雙速切換與生命週期鎖定機制 (1.0x / 0.75x)**：針對瀏覽器在給定 `audio.src` 時會自動將 `playbackRate` 洗白重置為 `defaultPlaybackRate (1.0)` 的底層機制，系統全面設定 `audio.defaultPlaybackRate = playbackRate`，並在 `loadedmetadata`、`canplay`、`play` 等多重事件中強制鎖定 `enforceRate()`，確保 0.75x 減速自然清晰。
  * **語音偏好本地持久化**：以 `localStorage` 保存 `thai_weekly_audio_rate`，讀者選定 0.75x 或 1.0x 後，跨期數閱讀、即時查詢或重整網頁皆自動記憶偏好。
* **相容性保證**：
  * 舊信件點擊 `26w41.html`、`26w42.html`、`26w43.html`、`26w44.html` 均自動無縫跳轉至 `lesson.html?issue=26wXX`，歷史連結 100% 正常開啟。

---

## 4. Google Apps Script 自動化中樞與安全防禦

* **綁定試算表**：`Thai_Weekly_DB`
* **Script ID**：[`1fJ_JIB0aET_pLwDOJasv47YzSBn3xk7NhW3h96919NRd2opJpq-VOOmA`](https://script.google.com/home/projects/1fJ_JIB0aET_pLwDOJasv47YzSBn3xk7NhW3h96919NRd2opJpq-VOOmA/edit)
* **線上指令碼編輯器**：[開啟 Google Apps Script 控制台](https://script.google.com/home/projects/1fJ_JIB0aET_pLwDOJasv47YzSBn3xk7NhW3h96919NRd2opJpq-VOOmA/edit)
* **Web App 執行端點**：`https://script.google.com/macros/s/AKfycbxiY6t8K_BmB2oRWhbi7UZCHpN1Blmd1BEH8APe3PW6gXCKX2XcNYHcDZhZfMZtifi4/exec`

### 4.1 試算表上方專屬操作選單
開啟試算表時，上方功能選單會自動出現 **「🚀 週報自動化控制台」**：
1. **▶️ 立即手動執行出刊與寄信**：手動立即觸發當週 AI 出刊流水線。
2. **📧 立即補寄 26w43 給 Annie 與 昌哥**：一鍵將 26w43 導讀信獨立補寄給 Annie 與 昌哥。
3. **⏰ 設定每週六 09:00 自動出刊排程**：一鍵建立每週六 09:00 的時間驅動排程。
4. **🧹 一鍵清理現有備忘重複前綴**：清理歷史文化備忘中重複的多餘標題前綴。
5. **🧩 自動補齊歷史單字說文解字 (Auto-Backfill)**：自動遍歷已發布期數之單字，呼叫 Gemini 自動分析補齊 F、G 欄說文解字資料。
6. **🔑 寫入/更新 GEMINI_API_KEY 至指令碼屬性**：一鍵彈出輸入對話框，將金鑰直接儲存至雲端指令碼屬性庫 (`ScriptProperties`)。

### 4.2 零暴露 API 金鑰安全管理機制 (Zero-Exposure Architecture)
* **完全消除硬編碼**：專案所有前端原始碼、後端 `Code.gs` 以及 Git Commit 歷史中，徹底杜絕任何真實 API Key 字串。
* **雲端屬性隔離儲存**：金鑰僅保存在 Google 雲端 `PropertiesService.getScriptProperties()` 中，由 GAS 內部環境沙盒隔離保護。
* **介面互動式更新**：使用者若更換金鑰，只需在試算表點選「🔑 寫入/更新 GEMINI_API_KEY」，於跳出的 `ui.prompt` 對話框輸入即可，永不落地於檔案。
* **端點驗證機制**：Web App `doPost` 支援 `check_key`（遮蔽預覽驗證）與 `set_key`，確保部署後可遠端確認金鑰持久化狀態。

### 4.3 即時構詞解析與歷史自動回填引擎
* **即時單字拆解 API (`analyzeSingleWord`)**：
  - 前端發起 `action: "analyze_word"`，後端支援 `doGet` 與 `doPost` 雙路由。
  - 模型採用最新 `gemini-3.5-flash-lite`（優先）與 `gemini-3.8-flash`（備援）。
  - 自動構詞辨識規範：複合詞強制拆解詞素與產出 2~3 個高頻派生詞；純外來語（如 Key card）或單字根（如 แพ้）一律回傳空陣列 `[]`，並提供構詞學備忘。
* **歷史自動回填函式 (`backfillAnatomyForIssue`)**：
  - 貫徹「零人工手動維護」原則，依期數自動撈取未拆解單字，批次呼叫 Gemini 生成標準 JSON，自動寫回 `Vocab` 工作表 F、G 欄。
* **匿名跨域權限部署 (`ANYONE_ANONYMOUS`)**：
  - `gas/appsscript.json` 配置 `"access": "ANYONE_ANONYMOUS"`，確保全體讀者於瀏覽器端免 Google 登入即可順暢調用 Web App 查詢端點。

### 4.4 收件人一對一寄信規範 (MailApp.sendEmail)
迴圈分三次個別獨立寄送，`To` 僅包含該位收件者，信首呈現專屬稱謂（嚴禁合併發送）：
1. `voyager.martin@gmail.com` ➔ `早安 Martin！`
2. `anniechen0209@gmail.com` ➔ `早安 Annie！`
3. `tienzitw@yahoo.com.tw` ➔ `早安 昌哥！`

---

## 5. 里程碑記錄 (Milestones)

- [x] **v1.0**：視覺風格升級為「大皇宮金箔 × 暹羅暗夜紫」雜誌風。
- [x] **v1.1**：完成 34px 大字級與 1160px/1240px 桌機沉浸式排版升級。
- [x] **v1.2**：解決 Google TTS 跨域播放問題，完成雙引擎語音備援機制。
- [x] **v1.3**：完成首頁「方案 1 ＋ 方案 4」檢索與折疊收納抽屜。
- [x] **v2.0**：移除本地排程依賴，上線 26w43 特輯與文化專題發音膠囊。
- [x] **v3.0 (重大架構升級 ｜ Sheet-as-a-CMS 與安全架構完善版)**：
  - [x] 建立結構化試算表資料庫 `Thai_Weekly_DB`（涵蓋 Issues, Vocab, Sentences, Grammar 四大分頁）。
  - [x] 將 26w41、26w42、26w43 完整解析入庫，並配置 26w44 預告資料列。
  - [x] 前端網站改為純動態即時渲染架構：建立 `lesson.html` 並升級 `index.html`。
  - [x] 舊期數檔案無縫配置重定向機制，確保歷史連結 100% 不失效。
  - [x] 建立綁定 Google Apps Script 中樞（含 Gemini 出刊生成、MailApp 一對一獨立寄信與自訂工具列選單）。
  - [x] 建立 API 金鑰雲端指令碼屬性 (`ScriptProperties`) 持久化與試算表彈窗輸入機制。
  - [x] 徹底清除原始碼硬編碼金鑰，重構淨化 Git 歷史紀錄（Purge Git History），達成零外洩資安防禦。
  - [x] 升級 `deploy_gas.py` 支援原地覆蓋部署，保持 Web App URL 恆定。
- [x] **v3.1 (全端動態渲染穩定化與語音體驗升級 ｜ 2026-10-31)**：
  - [x] 發布 VOL. 26w44 特輯（泰式按摩SPA・藥局問診與身體部位實務），並自動生成 26w45 預告。
  - [x] 排查並修復 GViz 查詢缺少 `&headers=1` 導致多筆字串列被啟發式演算法併入欄位標頭之重大缺陷。
  - [x] 排查並修復 HTML5 Audio 在指派 `src` 時自動重置 `playbackRate` 的底層機制，落實多事件鎖定與 `defaultPlaybackRate` 雙重防護。
  - [x] 提前實現 Roadmap「語音播放自訂記憶」：以 `localStorage` 持久化讀者速率偏好。
  - [x] 建立 `26w44.html` 跳轉頁，維持向下相容性。
  - [x] 確立「非必要勿開啟瀏覽器做測試」之核心除錯開發準則。
- [x] **v3.2 (說文解字・詞彙拆解 Word Anatomy 擴充版 ｜ 2026-10-31)**：
  - [x] 擴充 `Vocab` 工作表欄位 F (`breakdown_json`) 與欄位 G (`extensions_json`)，自動回填入庫 26w41～26w44 全 22 個重點複合詞拆解。
  - [x] 升級 `gas/Code.gs` Gemini Prompt（複合詞辨識、純外來語/單字根防呆排除）與歷史資料自動回填函式 `backfillAnatomyForIssue()`。
  - [x] 升級 `lesson.html` 採按鈕觸發折疊抽屜 (`.anatomy-drawer`)，解決左右卡片高度不均問題。
  - [x] 重構拆解積木為上下層次獨立卡片 (`.anatomy-item`)，徹底根除泰文折行斷字與按鈕外框溢出缺陷。
- [x] **v3.3 (即時 AI 詞典全站雙端同步與訂閱演進藍圖 ｜ 2026-10-31)**：
  - [x] 實作即時線上說文解字 API 端點 (`analyzeSingleWord`)，支援 `doGet` 與 `doPost` 雙通道，部署匿名跨域存取 (`ANYONE_ANONYMOUS`)。
  - [x] 前端 `lesson.html` 與首頁 `index.html` 雙端同步掛載「🧩 泰語說文解字・即時構詞詞典」，支援雙重傳輸容錯（POST 優先＋GET 備援）與全域字串跳脫保護。
  - [x] 首頁完整繼承雙引擎 TTS 語音播放與速度偏好記憶（`localStorage['thai_weekly_audio_rate']`）。
  - [x] 正式將「個人化語境客製與訂閱制引擎」演進方案寫入專案手冊第 6 節，作為後續開發基石。

---

## 6. 下階段開發演進展望 (Next Phase Roadmap)

本節作為後續迭代與學習體驗擴充的起點基準：

1. **學習歷程本地持久化 (Local Progress Tracking)**：
   * 利用瀏覽器 `localStorage` 記錄讀者的「已讀期數徽章」、「核心單字收藏本 (Saved Vocab)」。
   * 在首頁卡片上呈現輕量化已讀進度狀態（如：`✓ 已閱讀`）。
2. **單元測驗模式增強 (Interactive Learning Enhancements)**：
   * 提供更精細的「遮蔽模式」：獨立切換遮蔽「泰文單字」、「音標」或「中文釋義」。
   * 單元快速自測：於 `lesson.html` 底部整合隨機 3 題快速選擇測驗，即時檢視學習成效。
3. **語音播放自訂記憶 (Audio Preferences)**：
   * [x] 記憶讀者自選之語音速率（1.0x 或 0.75x），換頁時自動保持偏好（已於 v3.1 實現）。
   * 新增發音波形動畫或跟讀計時器。
4. **多媒體內容延伸 (Rich Media Support)**：
   * 評估在 Google Sheet 中增加欄位支援短影片嵌入（YouTube Shorts）或情境音檔直連，豐富每週文化專題深度。
5. **訂閱制與個人化語境客製引擎 (Personalized Context & Subscription Engine)**：
   * **核心願景**：突破通用教材限制，以「大盤共用＋個人客製 (Hybrid Prompting)」架構，提供與讀者個人生活、工作及興趣高度相關的專屬泰語學習語境。
   * **訂閱者輪廓資料庫 (`Subscribers` 工作表)**：
     - 規格規劃：`email` ｜ `nickname` ｜ `gender` ｜ `interest_tags` (如：馬拉松、金融經濟、網路科技、美食咖啡) ｜ `status` (active / inactive)。
   * **GAS 獨立發信客製注入 (MailApp Personal Patch)**：
     - 利用既有的一對一獨立寄信迴圈，在發送前以輕量 Prompt 結合當週核心句型與該讀者的 `interest_tags`，自動生成 1 組專屬情境句與 2 個延伸生活詞彙，無縫注入專屬信件導讀。
   * **網頁端動態個人化專欄 (Personalized Lesson Dynamic Slot)**：
     - 前端 `lesson.html?issue=YYwWW&uid={user_id}` 支援讀取個人參數，於課程底層動態長出「🎯 為你特調的專屬單字與情境卡」，不污染公版試算表與首頁歷史歸檔。
