# Thai_Weekly (泰語學習週報自動化發布系統) 專案協作手冊

> **專案版本**：v1.3 (雲端零接觸全自動部署版)  
> **最後更新日期**：2026-10-17  
> **維護者**：Martin × Gemini Spark × Antigravity (Anti)

---

## 1. 專案願景與協作架構

### 1.1 願景 (Vision)
打造一個**全自動、零手動維護、支援原地標準語音播放與卡片互動自測**的現代化泰語自主學習網站。讀者能每週定期獲取結合時事/日常話題的精選短篇教學，享有沈浸式泰國皇室紫金雜誌閱讀體驗與高效率自學工具。

### 1.2 三方協作流水線 (Collaborative Pipeline)

本專案由三方緊密分工形成 100% 雲端零接觸自動化生產流水線：

```mermaid
flowchart LR
    A["Martin (架構與業務主理)"] -->|教材源頭短篇維護| B["Google Drive (泰文小短篇)"]
    B -->|每週六 09:00 排程解析| C["Gemini Spark (內容引擎)"]
    C -->|產出結構化 YYwWW.html & index.html| B
    B -->|每週六 09:15~10:00 零接觸自動抓取| D["GitHub Actions (sync_drive.yml)"]
    D -->|Git Commit & Push (main)| E["GitHub Pages / 線上門戶"]
    style A fill:#1e293b,stroke:#38bdf8,color:#fff
    style B fill:#0f172a,stroke:#38bdf8,color:#fff
    style C fill:#1e293b,stroke:#ec4899,color:#fff
    style D fill:#1e293b,stroke:#a855f7,color:#fff
    style E fill:#0284c7,stroke:#f59e0b,color:#fff
```

* **Martin (專案推動 / 業務主理)**：
  * 定義業務需求、核心規範與風格偏好。
  * 於 Google Drive 目錄（`泰文小短篇`）存放與維護原生泰語素材、字彙手稿與參考材料。
  * 審閱線上站點學習成效、發音體驗與整體演進方向。
* **Gemini Spark (內容引擎 / 教學拆解)**：
  * 固化每週六 09:00 自動執行指令，將雲端短文智能剖析：斷詞音標（IPA / 羅馬拼音）、中文翻譯、核心文法點、難詞單字釋義。
  * 嚴格套用 `templates/lesson_template.html` 骨架生成當週獨立課程（`YYwWW.html`）與新版入口門戶（`index.html`）。
  * 產出每週「互動遮蔽測驗（Cloze / Flashcards）」題型數據與上下文例句，直接以原始 HTML 實體寫回 Google Drive。
* **Anti / Antigravity (系統工程 / 程式碼實作與自動化維運)**：
  * 負責維護全站靜態頁面模板、首頁紫金門戶架構與 UI 互動邏輯（大字級容器、方案 1 + 方案 4 搜尋收納）。
  * 建置 GitHub Actions 純雲端零接觸全自動排程管線（`sync_drive.yml`），解除本地 Cron 與個人電腦開機依賴。
  * 整合 Google TTS 搭配 Web Speech API 雙引擎語音播放器，並配置 `<meta name="referrer">` 防護。
  * 維護雙向同步與模板寫回工具，確保整套自動化系統穩定健壯。

---

## 2. 目錄與檔案結構規範 (File Structure & Naming Conventions)

### 2.1 外部雲端資料來源
* **目標 Google Drive 資料夾**：`泰文小短篇`
* **Folder ID**：`1xTWvfaAEIqzHFpDKtG7ipdMBZf8PYbBA`
* **重要備忘 (GCP Service Account 限制)**：
  * GCP 服務帳號本身具備 0 MB 儲存配額限制。
  * 在個人 Google Drive 中，模板（`lesson_template.html`）與手冊（`HANDBOOK.MD`）由主理人帳號建立後，自動化腳本可正常執行 `update` 覆蓋更新。

### 2.2 網站檔案結構與命名
發布端採用乾淨且易於歸檔的週期編號命名法則：

```text
Thai_Weekly/
├── .github/
│   └── workflows/
│       ├── sync_drive.yml      # 每週六 09:15~10:00 雲端定時零接觸向 Google Drive 自動同步
│       ├── sync.yml            # 原每週六 09:30 自動從 Google Drive 同步更新至 GitHub
│       └── upload_to_drive.yml # 一鍵手動推送本地最新模板與手冊至 Google Drive
├── templates/
│   └── lesson_template.html    # Spark 生成每週課程專用的標準紫金版 HTML 骨架
├── favicon.svg                 # 專屬深邃曜石黑 × 科技藍漸層泰語學習 App 圖標
├── index.html                  # 站點首頁（方案 1 置頂封面 + 方案 4 搜尋手風琴抽屜）
├── 26w41.html                  # 第 1 期課程實體頁（飲食預訂實務・語法名詞化與九皇齋節）
├── 26w42.html                  # 第 2 期課程實體頁（交通指引・機場退稅與水燈節前哨）
├── sync_drive_to_github.py     # Google Drive 雲端檔案自動拉取與 Git Push 腳本
├── upload_to_drive.py          # 本地模板寫回 Google Drive 工具腳本
├── HANDBOOK.MD                 # 本專案協作手冊（規格與最高指引）
└── README.md                   # 專案概覽與說明
```

* **入口頁面**：`index.html`（彙整所有歷史週報索引、即時關鍵字過濾與年度歸檔收納）。
* **每週獨立課程命名規則**：`YYwWW.html`
  * `YY`：公元年份後兩碼（例如 `2026` 年為 `26`）
  * `w`：固定小寫字母 `w`（表示 week）
  * `WW`：兩位數週次（01 ~ 53，例如第 41 週為 `41`，檔名即為 `26w41.html`）

---

## 3. 技術與 UI / UX 規範 (Design & Interaction System)

### 3.1 視覺風格：泰國皇室紫金風 (Dark Editorial Magazine UI - 暹羅暗夜紫與大皇宮金箔)
全站統一採用高對比、護眼且極具大皇宮金箔質感的配色系統：

* **核心 CSS 配色變數 (`:root`)**：
  ```css
  :root {
    /* 背景層次 */
    --bg-base: #0d0814;          /* 暹羅暗夜紫底（取代原石板黑） */
    --bg-surface: #170f24;       /* 皇室深紫表層 */
    --bg-card: #231738;          /* 帝王紫卡片背景 */
    --bg-card-hover: #2f1f4a;    /* 卡片懸浮高光 */
    --border: #443063;           /* 沉穩紫金邊框 */
    --border-accent: #f59e0b;    /* 泰皇金箔高光邊框 */

    /* 皇家金色系統（象徵大皇宮佛寺金箔與皇室尊爵） */
    --accent-gold: #f59e0b;       /* 泰皇金箔金（主要按鈕、標題裝飾） */
    --accent-gold-light: #fde68a; /* 亮香檳金（重點文字與標籤） */
    --text-thai: #fde047;         /* 泰文字級專屬金色（黑底金字極致辨識度） */
    --gold-glow: rgba(245, 158, 11, 0.28); /* 金色發光光暈 */

    /* 皇室紫色系統（泰國詩琳通公主與皇室經典代表色） */
    --primary: #a855f7;          /* 皇家紫羅蘭色（功能按鈕、標籤） */
    --primary-hover: #c084fc;    /* 亮紫高光 */
    --primary-glow: rgba(168, 85, 247, 0.3);

    /* 文字與中性色 */
    --text-main: #f8fafc;        /* 象牙白主文字 */
    --text-muted: #a78bfa;       /* 柔紫灰輔助次要文字 */
  }
  ```

* **雜誌封面橫幅**：
  ```css
  background: linear-gradient(135deg, #170f24 0%, #2e1065 60%, #451a03 100%);
  border-top: 2px solid var(--accent-gold);
  ```

### 3.2 容器與字體規格 (Typography & Layout)
* **大版面容器**：桌機主要容器寬度設定為 **1160px**（當視窗 `>= 1400px` 時自動擴展至 **1240px**），徹底解決大螢幕留白過多問題。
* **字級規格**：
  * **34px 核心泰語單字**：採用 `--text-thai: #fde047` 黑底金字，搭配金色柔光微陰影（`0 0 16px rgba(245, 158, 11, 0.35)`），音標符號清晰分明。
  * **25px 情境泰語句型**：加強實務跟讀辨識度。
  * **17.5px 正文閱讀**：行高設定為 1.7 ~ 1.8，搭配柔和象牙白（`#f8fafc`）。
* **語意斷句保護**：
  長句中的核心語意區塊以 `<span style="display:inline-block">` 包裹，防止中文/泰文在特定螢幕斷句突兀（例如：「專為職場接待與生活實務打造」）。

### 3.3 原地語音播放系統 (In-place TTS Dual Engine & Security)
為保證語音播放 100% 穩定零中斷，全站統一配置雙重防護機制：

1. **安全性與跨域防護（必備）**：
   ```html
   <meta name="referrer" content="no-referrer">
   ```
   * **關鍵作用**：移除請求中的 `Referer` 標頭，防止 Google TTS 伺服器因跨域或來源阻擋而返回 HTTP 404 / 播放失敗。
2. **雙引擎備援架構 (Dual-Engine Audio)**：
   * **第一引擎 (Primary)**：Google 繁中/泰語標準 TTS 原地串流 (`audio/mpeg`)。
   * **第二引擎 (Fallback)**：若遇到網路連線異常或跨域受阻，JavaScript 自動無縫切換至瀏覽器原生 **Web Speech API** (`SpeechSynthesisUtterance`，指定 `lang: 'th-TH'`)。
3. **播放控制**：
   * 支援原地動態波紋光暈（Pulse Glow）。
   * 具備 1.0x 標準速與 0.75x 慢速跟讀切換。

### 3.4 門戶首頁收納與檢索機制（方案 1 ＋ 方案 4）
為避免未來課程持續增加導致首頁卡片過多、滑動過長，`index.html` 整合了兩大收納機制：

1. **方案 1：視覺分層＋歷史年度收納抽屜**
   * **本週最新刊置頂大封面 (Spotlight Hero)**：永遠突顯當週最新一期，包含呼吸燈標籤、摘要、核心特點與一鍵直達按鈕。
   * **近期特輯展示區 (Recent Issues Grid)**：僅保留最近 4～6 期的紫金卡片展開，維持雜誌探索感。
   * **歷史年度手風琴抽屜 (Yearly Accordion Drawer)**：超過近期的舊期數依年份（如 📅 2026 年度課程歸檔）收納，**預設為折疊狀態**，保持首頁清爽簡潔。
2. **方案 4：毫秒級即時關鍵字搜尋與智慧聯動**
   * **檢索欄位**：支援刊號代碼（`26w41`）、主題關鍵字（`素食`、`預訂`）、單字與文法標籤。
   * **智慧展開聯動**：讀者輸入任意搜尋字詞時，前端自動**強制展開**所有歷史年度手風琴抽屜以進行全域檢索；清空關鍵字或按 `✕` 時，**自動恢復預設折疊**。
   * **即時統計回饋**：即時顯示「找到 X 筆相關課程」，無結果時跳出友善提示卡片。

---

## 4. 部署與自動化排程架構

### 4.1 GitHub Actions 工作流程
專案內建自動化 Actions：

1. **`.github/workflows/sync_drive.yml`（雲端零接觸全自動排程同步，主要）**：
   * 排程時間：台灣時間每週六上午 09:15、09:30、09:45、10:00 各觸發一次檢查（UTC 每週六 01:15、01:30、01:45、02:00）。
   * 功能：純雲端執行環境，透過 Google API 自動比對雲端「泰文小短篇」最新 `.html`，免開機、零接觸自動推送至 `main` 分支並觸發 GitHub Pages 部署。
2. **`.github/workflows/sync.yml`（備援同步管線）**：
   * 排程時間：台灣時間每週六上午 09:30（UTC 01:30，`cron: '30 1 * * 6'`）。
   * 功能：調用 Python 腳本下載雲端 HTML。
3. **`.github/workflows/upload_to_drive.yml`（一鍵推播模板）**：
   * 支援手動觸發（`workflow_dispatch`）。
   * 功能：將倉庫中最新修訂之 `lesson_template.html` 與 `HANDBOOK.MD` 自動更新回 Google Drive 目標資料夾。

### 4.2 必要的憑證設定 (GitHub Secrets)
* `GDRIVE_SA_KEY` / `GCP_SA_KEY_JSON`：Google Cloud 服務帳號金鑰（JSON 字串），服務帳號為 `thai-sync-bot@thai-weekly-sync.iam.gserviceaccount.com`，具備存取「泰文小短篇」資料夾（ID: `1xTWvfaAEIqzHFpDKtG7ipdMBZf8PYbBA`）之 Drive 權限。

---

## 5. Spark 生成每週週報之作業準則

Gemini Spark 於每週生成新期數（例如 `26w42.html`）時，必須遵守以下標準：
1. **骨架來源**：以 `templates/lesson_template.html` 為唯一基礎。
2. **視覺配色**：嚴格使用泰國皇室紫金配色變數（禁止改用舊版藍黑或石板灰）。
3. **安全標頭**：`<head>` 內必須包含 `<meta name="referrer" content="no-referrer">`。
4. **字級規範**：34px 核心單字、25px 情境句型、1160px 大版面容器。
5. **雙引擎語音**：完整保留 Google TTS + Web Speech API 語音函式。
6. **期數歸檔**：產生該期獨立網頁（如 `26w42.html`），並同步更新首頁 `index.html` 將最新一期置於 Spotlight Hero。

---

## 6. 結語與里程碑記錄

本手冊為全專案的最高指引原則。截至 2026-10-17，已達成：
- [x] 全站深色雜誌風升級為「大皇宮金箔 × 暹羅暗夜紫」主題。
- [x] 完成 34px 大字級與 1160px/1240px 桌機沉浸式排版升級。
- [x] 解決 Google TTS 播放失敗問題，完成 `<meta name="referrer">` 防護與 Web Speech API 雙引擎備援。
- [x] 完成首頁「方案 1 ＋ 方案 4」置頂封面、即時關鍵字搜尋與預設折疊年度手風琴抽屜。
- [x] 發布 26w42《交通指引・機場退稅與水燈節前哨》，並更新首頁 Spotlight Hero。
- [x] 升級為 100% 雲端零接觸全自動部署架構（`.github/workflows/sync_drive.yml`），解除本機設備與開機依賴。
- [x] 通過 GitHub Actions 實機排程驗證與 Service Account (`thai-sync-bot`) 雲端連線測試。

---

## 7. 下階段開發演進展望 (Next Phase Roadmap)

作為後續功能迭代與體驗擴充的起點記錄：

1. **學習歷程本地持久化 (Local Progress Tracking)**：
   * 透過瀏覽器 LocalStorage 記錄使用者「已讀期數」、「單字收藏」與「互動遮蔽測驗完成度」。
   * 於首頁卡片上呈現輕量化閱讀打勾進度徽章（例如：`✓ 已完成 80%`）。
2. **單元自測模式增強 (Flashcard & Cloze Enhancements)**：
   * 提供「一鍵全遮蔽 / 一鍵全顯示」快速切換功能（針對泰文字、音標、中文釋義分別開關）。
   * 支援隨機抽題與錯題集中複習功能。
3. **多媒體延伸整合 (Rich Media Integrations)**：
   * 探索情境對話短片、文化典故圖卡等多元富媒體嵌入。
   * 持續每週自動化排程生產發布（26w43...）。

