# Thai_Weekly (泰語學習週報自動化發布系統) 專案協作手冊

> **專案版本**：v3.0 (Google Sheet 結構化資料庫驅動架構 ｜ Sheet-as-a-CMS)  
> **最後更新日期**：2026-10-26  
> **維護者**：Martin × Antigravity (Anti) × Gemini API

---

## 1. 專案願景與協作架構 (Vision & Pipeline)

### 1.1 願景 (Vision)
打造一個**全自動、零手動維護、支援原地標準語音播放與卡片互動自測**的現代化泰語自主學習網站。全站採用**泰國皇室紫金風（Dark Editorial Magazine UI）**，支援雙引擎 TTS 語音發音與沉浸式大字級排版。

### 1.2 v3.0 結構化資料庫驅動架構 (Sheet-as-a-CMS)

在 v3.0 重構中，系統徹底邁向 **「Google Sheet-as-a-CMS 驅動架構」**，全面解決以下痛點：
- **消滅檔案搬移失敗與 Git Push 依賴**：每週出刊只需將結構化資料寫入 Google Sheet，前端網頁即時動態渲染出最新期數，徹底免去每週生成靜態 HTML 與 Git Commit Push 的維護負擔。
- **根絕真人確認卡與流程攔截**：採用 Google Apps Script 原生 `MailApp.sendEmail`，享受 Google 帳戶每日原生發信額度，無真人確認卡阻擋。
- **根除 404 找不到網頁時序爭執**：資料一入庫，前端 `lesson.html?issue=YYwWW` 隨即生效，信件中的閱讀按鈕點擊必有網頁！

```mermaid
flowchart TD
    A["時間驅動排程 (每週六 09:00 台北時間)"] --> B["Google Apps Script 執行 weeklyAutoPublish()"]
    B --> C["呼叫 Google Gemini API 產出教材 JSON (嚴格台灣繁中)"]
    C --> D["SpreadsheetApp 寫入 Google Sheet 四大分頁\n(Issues, Vocab, Sentences, Grammar)"]
    D --> E["資料入庫即刻生效！前端即時可用"]
    D --> F["MailApp.sendEmail 獨立發送 3 封一對一專屬問候信"]
    
    subgraph 前端即時讀取 (GitHub Pages)
        G["讀者造訪 index.html 或 lesson.html?issue=YYwWW"]
        G --> H["Google Visualization JSON API (GViz) 即時查詢試算表"]
        H --> I["動態渲染紫金首頁 Hero、手風琴歸檔或課程四大專欄"]
    end

    F --> G
    
    style A fill:#1e293b,stroke:#38bdf8,color:#fff
    style B fill:#1e293b,stroke:#a855f7,color:#fff
    style C fill:#0f172a,stroke:#38bdf8,color:#fff
    style D fill:#047857,stroke:#10b981,color:#fff
    style E fill:#0284c7,stroke:#f59e0b,color:#fff
    style F fill:#b45309,stroke:#f59e0b,color:#fff
    style G fill:#1e293b,stroke:#fde047,color:#fff
    style H fill:#1e293b,stroke:#38bdf8,color:#fff
    style I fill:#231738,stroke:#f59e0b,color:#fff
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
   - `issue_code` (如 26w43) ｜ `year` ｜ `week` ｜ `publish_date` ｜ `status` (published / upcoming) ｜ `title` ｜ `subtitle_1` ｜ `subtitle_2` ｜ `read_time` ｜ `highlights` ｜ `culture_title` ｜ `culture_body_html` ｜ `culture_memo_html` ｜ `email_subject` ｜ `email_intro_html` ｜ `email_highlights_html`
2. **`Vocab`（單字庫）**
   - `issue_code` ｜ `type` (`core` 核心字 / `culture` 文化專題單字) ｜ `thai` ｜ `phonetic` ｜ `meaning`
3. **`Sentences`（情境句型庫）**
   - `issue_code` ｜ `order` (1~5) ｜ `thai` ｜ `phonetic` ｜ `meaning`
4. **`Grammar`（語法解析庫）**
   - `issue_code` ｜ `point_num` (1~2) ｜ `title` ｜ `explanation_html` ｜ `examples_json` (例句陣列 JSON：`[{"thai": "...", "phonetic": "...", "meaning": "..."}]`)

---

## 3. 前端動態渲染系統架構 (Frontend Dynamic CMS)

```text
Thai_Weekly/
├── index.html                  # 站點首頁（即時讀取 Issues 分頁，動態渲染 Spotlight Hero、近期特輯與歷史手風琴）
├── lesson.html                 # 動態課程頁（依 ?issue=YYwWW 參數即時載入渲染四大專題，支援語音發音與遮蔽自測）
├── 26w41.html                  # 歷史相容跳轉頁（內嵌自動導向 lesson.html?issue=26w41）
├── 26w42.html                  # 歷史相容跳轉頁（內嵌自動導向 lesson.html?issue=26w42）
├── 26w43.html                  # 歷史相容跳轉頁（內嵌自動導向 lesson.html?issue=26w43）
├── favicon.svg                 # 專屬深邃曜石黑 × 科技藍漸層泰語學習 App 圖標
├── templates/
│   └── lesson_template.html    # 紫金版面設計基準模板（供動態骨架參考）
├── gas/
│   └── Code.gs                 # 綁定 Google Apps Script 原生自動化腳本
├── scripts/
│   ├── Thai_Weekly_DB.xlsx     # 結構化資料庫本地工作簿快照
│   ├── create_sheet_from_xlsx.py # 試算表轉換建立工具
│   ├── deploy_gas.py           # Google Apps Script 遠端程式碼部署工具
│   ├── parse_lessons.py        # 歷史 HTML 解析工具
│   └── db_config.json          # 資料庫 ID 與端點快照設定檔
└── HANDBOOK.MD                 # 本專案協作手冊（最高指導指引）
```

### 3.1 視覺與技術規範 (Design & Interaction System)
* **配色系統**：
  * 背景基底：`--bg-base: #0d0814` (暹羅暗夜紫底)
  * 卡片表層：`--bg-card: #231738` (帝王紫卡片)
  * 金箔高光：`--accent-gold: #f59e0b` (泰皇金箔金)
  * 泰文專屬：`--text-thai: #fde047` (黑底金字 34px 大字體)
* **字級與容器**：
  * 桌機容器寬度：1160px（大螢幕自動擴展至 1240px）。
  * 核心單字 34px、情境例句 25px、內文 17.5px。
* **安全標頭**：`<meta name="referrer" content="no-referrer">`。
* **雙引擎語音播放系統**：
  * 第一引擎：Google TTS 原地串流 (`audio/mpeg`)。
  * 第二引擎：自動備援 Web Speech API 原生合成語音 (`th-TH`)。
  * 文化專題精選單字發音：文末必備 8 組文化單字發音按鈕 (`culture-vocab-sec`) 🔊。
* **相容性保證**：
  * 舊信件點擊 `26w41.html`、`26w42.html`、`26w43.html` 均自動無縫跳轉至 `lesson.html?issue=26wXX`，舊連結 100% 正常開啟。

---

## 4. Google Apps Script 自動化中樞

* **綁定試算表**：`Thai_Weekly_DB`
* **Script ID**：[`1fJ_JIB0aET_pLwDOJasv47YzSBn3xk7NhW3h96919NRd2opJpq-VOOmA`](https://script.google.com/home/projects/1fJ_JIB0aET_pLwDOJasv47YzSBn3xk7NhW3h96919NRd2opJpq-VOOmA/edit)
* **線上指令碼編輯器**：[開啟 Google Apps Script 控制台](https://script.google.com/home/projects/1fJ_JIB0aET_pLwDOJasv47YzSBn3xk7NhW3h96919NRd2opJpq-VOOmA/edit)

### 4.1 試算表上方專屬操作選單
開啟試算表時，上方功能選單會自動出現 **「🚀 週報自動化控制台」**：
1. **▶️ 立即手動執行出刊與寄信**：手動立即觸發當週 AI 出刊流水線。
2. **📧 立即補寄 26w43 給 Annie 與 昌哥**：一鍵將 26w43 導讀信獨立補寄給 Annie 與 昌哥。
3. **⏰ 設定每週六 09:00 自動出刊排程**：一鍵建立每週六 09:00 的時間驅動排程。
4. **🔑 寫入/更新 GEMINI_API_KEY 至指令碼屬性**：一鍵將 Gemini API 金鑰持久化寫入指令碼屬性 (`PropertiesService.getScriptProperties`)。

### 4.2 API 金鑰管理機制 (Script Properties)
* **指令碼屬性**：全面採用 Apps Script 雲端原生指令碼屬性庫 (`PropertiesService.getScriptProperties`)，專案程式碼與 Git 倉庫中絕不硬編碼任何 API Key。
* **安全維護**：可隨時透過試算表頂部選單「🚀 週報自動化控制台 ➔ 🔑 寫入/更新 GEMINI_API_KEY」彈窗更新金鑰，零外洩風險。

### 4.3 收件人一對一寄信規範 (MailApp.sendEmail)
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
- [x] **v3.0 (重大架構升級 ｜ Sheet-as-a-CMS)**：
  - [x] 建立結構化試算表資料庫 `Thai_Weekly_DB`（涵蓋 Issues, Vocab, Sentences, Grammar 四大分頁）。
  - [x] 將 26w41、26w42、26w43 完整解析入庫，並配置 26w44 預告資料列。
  - [x] 前端網站改為純動態即時渲染架構：建立 `lesson.html` 並升級 `index.html`。
  - [x] 舊期數檔案無縫配置重定向機制，確保歷史連結 100% 不失效。
  - [x] 建立綁定 Google Apps Script 中樞（含 Gemini 出刊生成、MailApp 一對一獨立寄信與自訂工具列選單）。

---

## 6. 下階段開發演進展望 (Next Phase Roadmap)

本節作為 v3.0 穩定運行後，後續迭代與學習體驗擴充的起點基準：

1. **學習歷程本地持久化 (Local Progress Tracking)**：
   * 利用瀏覽器 `localStorage` 記錄讀者的「已讀期數徽章」、「核心單字收藏本 (Saved Vocab)」。
   * 在首頁卡片上呈現輕量化已讀進度狀態（如：`✓ 已閱讀`）。
2. **單元測驗模式增強 (Interactive Learning Enhancements)**：
   * 提供更精細的「遮蔽模式」：獨立切換遮蔽「泰文單字」、「音標」或「中文釋義」。
   * 單元快速自測：於 `lesson.html` 底部整合隨機 3 題快速選擇測驗，即時檢視學習成效。
3. **語音播放自訂記憶 (Audio Preferences)**：
   * 記憶讀者自選之語音速率（1.0x 或 0.75x），換頁時自動保持偏好。
   * 新增發音波形動畫或跟讀計時器。
4. **多媒體內容延伸 (Rich Media Support)**：
   * 評估在 Google Sheet 中增加欄位支援短影片嵌入（YouTube Shorts）或情境音檔直連，豐富每週文化專題深度。
