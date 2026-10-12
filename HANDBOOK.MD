# Thai_Weekly (泰語學習週報自動化發布系統) 專案協作手冊

> **專案版本**：v1.0  
> **最後更新日期**：2026-10-12  
> **維護者**：Martin × Gemini Spark × Antigravity (Anti)

---

## 1. 專案願景與協作架構

### 1.1 願景 (Vision)
打造一個**全自動、零手動維護、支援原地標準語音播放與卡片互動自測**的現代化泰語自主學習網站。讀者能每週定期獲取結合時事/日常話題的精選短篇教學，享有沉浸式的深色雜誌閱讀體驗與高效率自學工具。

### 1.2 三方協作流水線 (Collaborative Pipeline)

本專案由三方緊密分工形成自動化生產流水線：

```mermaid
flowchart LR
    A["Martin (架構與監護)"] -->|需求制定 & 源頭短篇提供| B["Google Drive (泰文小短篇)"]
    B -->|自動讀取| C["GitHub Actions CI/CD"]
    C -->|Prompt / 教材拆解| D["Gemini Spark (教材生成)"]
    D -->|結構化文章/生詞/測驗| E["Anti 構建腳本 (HTML 生成)"]
    E -->|產出每週課程 YYwWW.html| F["GitHub Pages / 線上站點"]
    style A fill:#1e293b,stroke:#38bdf8,color:#fff
    style B fill:#0f172a,stroke:#38bdf8,color:#fff
    style C fill:#1e293b,stroke:#a855f7,color:#fff
    style D fill:#1e293b,stroke:#ec4899,color:#fff
    style E fill:#0f172a,stroke:#22c55e,color:#fff
    style F fill:#0284c7,stroke:#38bdf8,color:#fff
```

* **Martin (專案推動 / 業務主理)**：
  * 定義業務需求、核心規範與風格偏好。
  * 於指定 Google Drive 目錄存放或維護原生泰語短篇材料。
  * 審閱線上站點學習反饋與整體發展方向。
* **Gemini Spark (內容引擎 / 教學拆解)**：
  * 負責將 Google Drive 上的短文進行智能剖析：斷詞音標（IPA / 羅馬拼音）、中文翻譯、核心文法點、難詞單字釋義。
  * 生成每週「互動遮蔽測驗（Cloze / Flashcards）」的題型數據與上下文例句。
* **Anti / Antigravity (系統工程 / 程式碼實作與自動化維運)**：
  * 負責靜態頁面模板（Template Engine）與建構邏輯（Builder Script）。
  * 串接 Google Drive API 與自動化同步機制。
  * 整合 Google TTS 語音發音元件、音訊快取與深色雜誌 UI 互動邏輯。
  * 配置 GitHub Actions 雲端定期排程發布與部署維護。

---

## 2. 目錄與命名規範 (File Structure & Naming Conventions)

### 2.1 外部資料來源
* **目標 Google Drive 資料夾**：`泰文小短篇`
* **Folder ID**：`1xTWvfaAEIqzHFpDKtG7ipdMBZf8PYbBA`
* **同步邏輯**：系統會自動抓取此資料夾內新增或更新的短篇文件，轉譯為每週刊發的獨立教材。

### 2.2 網站檔案結構與命名
發布端採用乾淨且易於歸檔的週期編號命名法則：

```text
Thai_Weekly/
├── .github/
│   └── workflows/
│       └── sync-and-deploy.yml  # GitHub Actions 定時排程與部署腳本
├── scripts/
│   ├── fetch_drive.py          # Google Drive 內容抓取
│   ├── generate_content.py     # Gemini Spark 教材處理腳本
│   └── build_site.py           # 靜態 HTML 生成器
├── templates/
│   ├── base.html               # 共通版型
│   └── lesson.html             # 單期課程範本
├── public/                     # 最終發布靜態檔案目錄 (或根目錄)
│   ├── index.html              # 站點首頁 (課程期數列表、進度追蹤、精選推薦)
│   ├── 26w41.html              # 每週獨立課程 (格式: YYwWW.html，例: 2026年第41週)
│   ├── 26w42.html
│   ├── assets/
│   │   ├── css/
│   │   │   └── magazine.css    # 深色雜誌風 UI 樣式表
│   │   └── js/
│   │       ├── player.js       # 原地 Google TTS 語音串流控制
│   │       └── quiz.js         # 互動遮蔽測驗與翻轉卡片邏輯
├── HANDBOOK.MD                 # 本專案協作手冊
└── README.md                   # 專案概覽與說明
```

* **入口頁面**：`index.html`（自動彙整所有歷史週報索引、提供學習進度追蹤與快捷搜尋）。
* **每週獨立課程命名規則**：`YYwWW.html`
  * `YY`：公元年份後兩碼（例如 `2026` 年為 `26`）
  * `w`：固定小寫字母 `w`（表示 week）
  * `WW`：兩位數週次（01 ~ 53，例如第 41 週為 `41`，檔名即為 `26w41.html`）

---

## 3. 技術與 UI / UX 規範 (Design & Interaction System)

### 3.1 視覺風格：深色雜誌風 (Dark Editorial Magazine UI - 暹羅暗夜紫與大皇宮金箔)
* **色彩基調 (Color Palette)**：
  * 主背景 (Background)：`#0d0814`（暹羅暗夜紫底）至 `#170f24`（皇室深紫表層）。
  * 卡片/區塊 (Surface)：`#231738`（帝王紫卡片背景），沉穩紫金邊框 `#443063`，懸浮高光 `#2f1f4a`。
  * 皇家金箔系統 (Accent Gold)：泰皇金箔金 (`#f59e0b`)、亮香檳金 (`#fde68a`)、泰文字級專屬金色 (`#fde047` 黑底金字極致辨識度)。
  * 皇室紫系統 (Primary)：詩琳通公主皇室紫羅蘭色 (`#a855f7`)、亮紫高光 (`#c084fc`)。
  * 封面橫幅：皇室紫漸層 `linear-gradient(135deg, #170f24 0%, #2e1065 60%, #451a03 100%)` 搭配金色細頂邊。
  * 文字階層 (Typography)：
    * 主標題與泰文字體：採用清晰優美的現代字型（如 `Noto Sans Thai`、`Sarabun`）。
    * 正文字體：高品質現代無襯線字體（如 `Inter`、`system-ui`）。
* **字體大小階層 (Font Scale)**：
  * **核心泰語單字/片語**：**28px**（加粗，間距舒展，確保聲調符號清晰易讀）。
  * 拼音/音標 (Phonetic / Transliteration)：15px（柔和輔助灰 `#94a3b8`）。
  * 中文釋義與說明：16px - 18px。
  * 課文本文 (Body Text)：泰文 22px / 中文對照 16px。

### 3.2 原地 Google TTS 串流播放 (In-place TTS Audio Player)
* **標準語音串流**：
  * 點擊任何單字、例句或段落旁的播放按鈕，即時發起 Google TTS（泰語 `th-TH`）音訊串流。
  * **原地播放**：不另開分頁、不跳轉視窗，播放時該卡片/字詞呈現動態發光波紋（Pulse Animation）。
* **播放控制**：支援 1.0x 標準速與 0.75x 慢速跟讀重播功能。

### 3.3 互動遮蔽測驗 (Interactive Masking & Self-test)
* **自測卡片 (Cloze / Masked Cards)**：
  * 重點單字預設呈現霧面毛玻璃遮蔽（Blur / Mask）。
  * 點擊/懸停即揭曉拼音與中文釋義，方便讀者先聽聲音或看泰文字母自測記憶。
* **隨堂複習小卡**：
  * 雙面翻轉卡（Flip Card）機制，支援標記「已掌握 / 需加強」。

---

## 4. 部署架構：方案 B (雲端定時排程自動同步與發布)

採用 **方案 B**：利用 Google Drive API + GitHub Actions 達成 100% 雲端全自動化運作，本機無需開啟常駐程序。

### 4.1 運作流程
1. **定時觸發 (Schedule Trigger)**：
   * GitHub Actions 依 Cron 排程（例如每週一上午 06:00 UTC+8）或 Repository Dispatch 自動喚醒。
2. **Drive 檔案偵測與拉取 (Drive Sync)**：
   * 透過 Google Drive Service Account API，掃描目標資料夾（ID: `1xTWvfaAEIqzHFpDKtG7ipdMBZf8PYbBA`）。
   * 比對現存期數，若發現未處理短篇或最新修訂，自動下載文字內容。
3. **AI 處理與頁面構建 (Content Build)**：
   * 呼叫腳本進行語意拆解、斷詞、注音、例句生成與課後測驗數據封裝。
   * 產出該週課程 `YYwWW.html` 並自動刷新 `index.html` 彙整首頁。
4. **自動發布 (Git Commit & Pages Deploy)**：
   * GitHub Actions 將產出的 HTML/靜態資產自動 Commit 回倉庫，並觸發 GitHub Pages 部署上線。

### 4.2 必要的憑證與環境變數 (Secrets)
* `GDRIVE_SERVICE_ACCOUNT_KEY`：Google Cloud 服務帳號 JSON 金鑰（需具備對目標雲端硬碟資料夾的讀取權限）。
* `GEMINI_API_KEY`：教材自動剖析與生詞拆解所需之 API Key。

---

## 5. 結語與準則 (Commitment)
本手冊為全專案的最高指引原則，後續所有頁面模板撰寫、自動化腳本實作與樣式調整均需嚴格遵守上述命名、視覺規範與自動化架構。
