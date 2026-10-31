/**
 * Thai_Weekly (泰語學習週報) Google Apps Script 後端中樞
 * 綁定試算表: Thai_Weekly_DB（泰語學習週報資料庫）
 * 試算表 ID: 1DvxPjzNRlTRSMSXr6eaktU2dBQZSS9oWadNfT3_ZUTM
 * 
 * 功能亮點：
 * 1. 結構化資料庫管理 (Issues, Vocab, Sentences, Grammar)
 * 2. 每週六 09:00 時間驅動排程自動呼叫 Gemini API 產出當週教材
 * 3. 獨立一對一發送專屬紫金雜誌風導讀信 (MailApp.sendEmail，0 真人確認卡)
 * 4. 試算表上方專屬工具列選單「🚀 週報自動化控制台」
 */

const SPREADSHEET_ID = "1DvxPjzNRlTRSMSXr6eaktU2dBQZSS9oWadNfT3_ZUTM";

const RECIPIENTS = [
  { name: "Martin", email: "voyager.martin@gmail.com", greeting: "早安 Martin！" },
  { name: "Annie", email: "anniechen0209@gmail.com", greeting: "早安 Annie！" },
  { name: "昌哥", email: "tienzitw@yahoo.com.tw", greeting: "早安 昌哥！" }
];

/**
 * 試算表開啟時自動建立頂部自訂控制台選單
 */
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu("🚀 週報自動化控制台")
    .addItem("▶️ 立即手動執行出刊與寄信", "weeklyAutoPublish")
    .addItem("📧 立即補寄 26w43 給 Annie 與 昌哥", "resend26w43ToAnnieAndChang")
    .addSeparator()
    .addItem("⏰ 設定每週六 09:00 自動出刊排程", "setupWeeklyTrigger")
    .addItem("🧹 一鍵清理現有備忘重複前綴", "cleanExistingMemos")
    .addItem("🧩 自動補齊歷史單字說文解字 (Auto-Backfill)", "menuBackfillAnatomy")
    .addItem("🔑 寫入/更新 GEMINI_API_KEY 至指令碼屬性", "setScriptProperties")
    .addToUi();
}

/**
 * 寫入 GEMINI_API_KEY 至指令碼屬性 (Script Properties)
 * 支援試算表彈窗輸入，亦支援程式化參數傳入
 */
function setScriptProperties(customKey) {
  let key = customKey;
  if (!key && SpreadsheetApp.getUi) {
    try {
      const ui = SpreadsheetApp.getUi();
      const resp = ui.prompt("設定 Gemini API Key", "請貼上您的全新 GEMINI_API_KEY：", ui.ButtonSet.OK_CANCEL);
      if (resp.getSelectedButton() === ui.Button.OK) {
        key = resp.getResponseText().trim();
      } else {
        return { status: "cancelled", msg: "使用者取消輸入" };
      }
    } catch (e) {
      Logger.log("非 UI 執行環境: " + e);
    }
  }

  if (!key) {
    const errorMsg = "未提供金鑰，無法設定！";
    if (SpreadsheetApp.getUi) {
      try { SpreadsheetApp.getUi().alert("錯誤", errorMsg, SpreadsheetApp.getUi().ButtonSet.OK); } catch(e){}
    }
    return { status: "error", msg: errorMsg };
  }

  PropertiesService.getScriptProperties().setProperty("GEMINI_API_KEY", key);
  Logger.log("GEMINI_API_KEY 已成功儲存至 Script Properties！");
  if (SpreadsheetApp.getUi) {
    try {
      SpreadsheetApp.getUi().alert("設定成功", "GEMINI_API_KEY 已成功寫入 Apps Script 指令碼屬性！", SpreadsheetApp.getUi().ButtonSet.OK);
    } catch (e) {}
  }
  return { status: "success", msg: "GEMINI_API_KEY 已成功儲存至 Script Properties" };
}

function getApiKey() {
  const prop = PropertiesService.getScriptProperties().getProperty("GEMINI_API_KEY");
  if (!prop) {
    throw new Error("尚未設定 GEMINI_API_KEY！請透過試算表上方選單「🚀 週報自動化控制台 ➔ 🔑 寫入/更新 GEMINI_API_KEY」輸入金鑰。");
  }
  return prop;
}

function doGet(e) {
  if (e && e.parameter && e.parameter.clean === "1") {
    const res = cleanExistingMemos();
    return ContentService.createTextOutput(JSON.stringify(res)).setMimeType(ContentService.MimeType.JSON);
  }
  const prop = PropertiesService.getScriptProperties().getProperty("GEMINI_API_KEY");
  return ContentService.createTextOutput(JSON.stringify({
    status: "ok",
    spreadsheet_id: SPREADSHEET_ID,
    has_script_property: Boolean(prop),
    timestamp: new Date().toISOString()
  })).setMimeType(ContentService.MimeType.JSON);
}

function doPost(e) {
  try {
    const postData = JSON.parse(e.postData.contents);
    const action = postData.action;

    if (action === "clean_memos") {
      const res = cleanExistingMemos();
      return ContentService.createTextOutput(JSON.stringify(res)).setMimeType(ContentService.MimeType.JSON);

    } else if (action === "init_vocab_anatomy" || action === "backfill_anatomy") {
      const res = backfillAnatomyForIssue(postData.issue_code);
      return ContentService.createTextOutput(JSON.stringify(res)).setMimeType(ContentService.MimeType.JSON);
    } else if (action === "publish_weekly") {
      const res = weeklyAutoPublish();
      return ContentService.createTextOutput(JSON.stringify(res)).setMimeType(ContentService.MimeType.JSON);
    } else if (action === "resend_26w43") {
      const res = resend26w43ToAnnieAndChang();
      return ContentService.createTextOutput(JSON.stringify(res)).setMimeType(ContentService.MimeType.JSON);
    } else if (action === "setup_trigger") {
      setupWeeklyTrigger();
      return ContentService.createTextOutput(JSON.stringify({ status: "success", msg: "Trigger created for Saturday 09:00" })).setMimeType(ContentService.MimeType.JSON);
    } else if (action === "check_key") {
      const prop = PropertiesService.getScriptProperties().getProperty("GEMINI_API_KEY");
      return ContentService.createTextOutput(JSON.stringify({
        has_script_property: Boolean(prop),
        key_masked: prop ? (prop.slice(0, 6) + "..." + prop.slice(-4)) : null
      })).setMimeType(ContentService.MimeType.JSON);
    } else if (action === "set_key") {
      const keyToSet = postData.key;
      const res = setScriptProperties(keyToSet);
      return ContentService.createTextOutput(JSON.stringify(res)).setMimeType(ContentService.MimeType.JSON);
    } else {
      return ContentService.createTextOutput(JSON.stringify({ status: "error", msg: "Unknown action" })).setMimeType(ContentService.MimeType.JSON);
    }
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ status: "error", error: err.toString() })).setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * 立即補寄 26w43 給 Annie 與 昌哥 (Martin 本人已收到)
 */
function resend26w43ToAnnieAndChang() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheetIssues = ss.getSheetByName("Issues");
  const data = sheetIssues.getDataRange().getValues();

  let targetRow = null;
  for (let i = 1; i < data.length; i++) {
    if (data[i][0] === "26w43") {
      targetRow = data[i];
      break;
    }
  }

  if (!targetRow) {
    const msg = "試算表中找不到 26w43 期數資料！";
    Logger.log(msg);
    if (SpreadsheetApp.getUi) {
      try { SpreadsheetApp.getUi().alert("錯誤", msg, SpreadsheetApp.getUi().ButtonSet.OK); } catch(e){}
    }
    return { status: "error", msg: msg };
  }

  const issueInfo = {
    issue_code: "26w43",
    title: targetRow[5],
    subtitle_1: targetRow[6],
    subtitle_2: targetRow[7],
    publish_date: targetRow[3],
    email_subject: "【泰語學習週報】VOL. 26w43 ｜ 微笑之國的款待密碼：從星級飯店 Check-in 到「ใจเย็นๆ」的高情商溝通藝術",
    email_intro_html: targetRow[14],
    email_highlights_html: targetRow[15]
  };

  const targetList = [
    { name: "Annie", email: "anniechen0209@gmail.com", greeting: "早安 Annie！" },
    { name: "昌哥", email: "tienzitw@yahoo.com.tw", greeting: "早安 昌哥！" }
  ];

  const sent = [];
  targetList.forEach(r => {
    sendPersonalizedEmail(r, issueInfo);
    sent.push(r.email);
  });

  const successMsg = "成功補寄 26w43 導讀信至:\n" + sent.join("\n");
  Logger.log(successMsg);
  try {
    SpreadsheetApp.getUi().alert("補寄成功", successMsg, SpreadsheetApp.getUi().ButtonSet.OK);
  } catch (e) {}

  return { status: "success", sent_to: sent };
}

/**
 * 發送一對一專屬信件 (使用 MailApp，無額度阻礙)
 */
function sendPersonalizedEmail(recipient, issueInfo) {
  const htmlBody = buildEmailHtml(recipient.name, issueInfo);
  MailApp.sendEmail({
    to: recipient.email,
    subject: issueInfo.email_subject,
    htmlBody: htmlBody,
    name: "Thai Weekly (泰語學習週報)"
  });
  Logger.log("已寄送給: " + recipient.name + " <" + recipient.email + ">");
}

/**
 * 組裝皇室紫金 HTML 電子報
 */
function buildEmailHtml(recipientName, issueInfo) {
  const lessonUrl = "https://voyagermartin.github.io/Thai_Weekly/lesson.html?issue=" + issueInfo.issue_code;
  
  return `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0d0814; color: #f8fafc; margin: 0; padding: 24px; }
  .email-container { max-width: 640px; margin: 0 auto; background: #170f24; border: 1px solid #443063; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
  .header { background: linear-gradient(135deg, #231738 0%, #3b1d61 100%); padding: 32px 28px; border-bottom: 2px solid #f59e0b; }
  .tag { display: inline-block; background: rgba(245, 158, 11, 0.2); color: #fde68a; border: 1px solid #f59e0b; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 700; letter-spacing: 0.5px; margin-bottom: 12px; }
  .title { color: #ffffff; font-size: 24px; font-weight: 800; margin: 0 0 8px 0; line-height: 1.35; }
  .subtitle { color: #cbd5e1; font-size: 15px; margin: 0; line-height: 1.6; }
  .content { padding: 28px; }
  .greeting { font-size: 17px; font-weight: 700; color: #fde68a; margin-bottom: 16px; }
  .intro-text { font-size: 15.5px; line-height: 1.8; color: #e2e8f0; margin-bottom: 24px; }
  .highlight-card { background: #231738; border: 1px solid #443063; border-left: 4px solid #f59e0b; border-radius: 10px; padding: 18px 20px; margin-bottom: 24px; }
  .highlight-title { font-size: 16px; font-weight: 700; color: #fde047; margin-bottom: 12px; }
  .highlight-item { font-size: 14.5px; line-height: 1.7; color: #cbd5e1; margin-bottom: 10px; }
  .btn-wrapper { text-align: center; margin: 32px 0 24px 0; }
  .btn-cta { display: inline-block; background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: #0d0814 !important; font-size: 16px; font-weight: 800; text-decoration: none; padding: 14px 32px; border-radius: 30px; box-shadow: 0 4px 18px rgba(245, 158, 11, 0.35); }
  .footer { background: #0f0a18; padding: 20px 28px; text-align: center; border-top: 1px solid #231738; font-size: 13px; color: #a78bfa; line-height: 1.6; }
  .footer a { color: #fde68a; text-decoration: none; }
</style>
</head>
<body>
<div class="email-container">
  <div class="header">
    <div class="tag">VOL. ${issueInfo.issue_code} ｜ 泰國皇室紫金特輯</div>
    <h1 class="title">${issueInfo.title}</h1>
    <p class="subtitle">${issueInfo.subtitle_1} ${issueInfo.subtitle_2}</p>
  </div>
  
  <div class="content">
    <div class="greeting">早安 ${recipientName}！</div>
    
    <div class="intro-text">
      ${issueInfo.email_intro_html}
    </div>

    <div class="highlight-card">
      <div class="highlight-title">✨ 本期三大核心專欄亮點</div>
      ${issueInfo.email_highlights_html}
    </div>

    <div class="btn-wrapper">
      <a href="${lessonUrl}" class="btn-cta">
        👉 點此前往 ${issueInfo.issue_code} 線上數位雜誌特輯
      </a>
      <div style="font-size: 13px; color: #a78bfa; margin-top: 10px;">
        💡 支援網頁原地 1.0x / 0.75x 雙引擎語音播放、文化單字發音與卡片遮蔽記憶測驗
      </div>
    </div>
  </div>

  <div class="footer">
    泰語學習週報｜全期索引門戶：<a href="https://voyagermartin.github.io/Thai_Weekly/index.html">voyagermartin.github.io/Thai_Weekly</a><br>
    由 Google Apps Script 全自動排程出刊 ｜ 敬祝閱讀愉快，週末充實順遂！
  </div>
</div>
</body>
</html>`;
}

/**
 * 設定每週六 09:00 自動執行的觸發器
 */
function setupWeeklyTrigger() {
  const triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(t => {
    if (t.getHandlerFunction() === "weeklyAutoPublish") {
      ScriptApp.deleteTrigger(t);
    }
  });

  ScriptApp.newTrigger("weeklyAutoPublish")
    .timeBased()
    .onWeekDay(ScriptApp.WeekDay.SATURDAY)
    .atHour(9)
    .inTimezone("Asia/Taipei")
    .create();

  const msg = "每週六 09:00 排程觸發器設定完成！";
  Logger.log(msg);
  try {
    SpreadsheetApp.getUi().alert("排程設定", msg, SpreadsheetApp.getUi().ButtonSet.OK);
  } catch (e) {}
}

/**
 * 每週六 09:00 全自動出刊中樞
 */
function weeklyAutoPublish() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheetIssues = ss.getSheetByName("Issues");
  const data = sheetIssues.getDataRange().getValues();

  // 尋找 upcoming 期數
  let upcomingRowIndex = -1;
  let upcomingIssue = null;
  for (let i = 1; i < data.length; i++) {
    if (data[i][4] === "upcoming") {
      upcomingRowIndex = i + 1;
      upcomingIssue = {
        code: data[i][0],
        title: data[i][5],
        desc: data[i][6] + " " + data[i][7]
      };
      break;
    }
  }

  if (!upcomingIssue) {
    Logger.log("無 upcoming 期數，自動跳過出刊。");
    return { status: "skipped", msg: "No upcoming issue found" };
  }

  Logger.log("開始編纂當週教材: " + upcomingIssue.code + " " + upcomingIssue.title);

  // 呼叫 Gemini API
  const generated = callGeminiGenerate(upcomingIssue);

  // 1. 更新 Issues 表該列為 published
  sheetIssues.getRange(upcomingRowIndex, 5).setValue("published");
  sheetIssues.getRange(upcomingRowIndex, 6).setValue(generated.issue_title);
  sheetIssues.getRange(upcomingRowIndex, 7).setValue(generated.subtitle_part_1);
  sheetIssues.getRange(upcomingRowIndex, 8).setValue(generated.subtitle_part_2);
  sheetIssues.getRange(upcomingRowIndex, 9).setValue(generated.read_time_minutes + " 分鐘");
  sheetIssues.getRange(upcomingRowIndex, 10).setValue(generated.highlights_summary);
  sheetIssues.getRange(upcomingRowIndex, 11).setValue(generated.culture.title);
  sheetIssues.getRange(upcomingRowIndex, 12).setValue(generated.culture.paragraphs.map(p => "<p>" + p + "</p>").join("\n"));
  let cleanCallout = (generated.culture.callout || "").trim();
  cleanCallout = cleanCallout.replace(/^(<b>)?\s*💡?\s*線控經理實務備忘[（(][^）)]*[）)][:：]?\s*(<\/b>)?\s*(<br\s*\/?>)?/i, "").trim();
  sheetIssues.getRange(upcomingRowIndex, 13).setValue(cleanCallout);
  sheetIssues.getRange(upcomingRowIndex, 14).setValue(generated.email.subject_line);
  sheetIssues.getRange(upcomingRowIndex, 15).setValue(generated.email.intro_text);
  sheetIssues.getRange(upcomingRowIndex, 16).setValue(generated.email.highlights.map(h => '<div class="highlight-item">' + h + '</div>').join("\n"));

  // 2. 寫入 Vocab (Core + Culture，擴充欄位 F: breakdown_json 與 G: extensions_json)
  const sheetVocab = ss.getSheetByName("Vocab");
  if (!sheetVocab.getRange(1, 6).getValue()) {
    sheetVocab.getRange(1, 6, 1, 2).setValues([["breakdown_json", "extensions_json"]]);
  }
  const vocabRows = [];
  generated.vocab.forEach(v => {
    const breakdownStr = (Array.isArray(v.breakdown) && v.breakdown.length > 0) ? JSON.stringify(v.breakdown) : "";
    const extensionsStr = (Array.isArray(v.extensions) && v.extensions.length > 0) ? JSON.stringify(v.extensions) : "";
    vocabRows.push([
      upcomingIssue.code,
      "core",
      v.thai,
      v.phonetic,
      v.pos + " " + v.meaning,
      breakdownStr,
      extensionsStr
    ]);
  });
  generated.culture.vocab_items.forEach(cv => {
    vocabRows.push([
      upcomingIssue.code,
      "culture",
      cv.thai,
      cv.phonetic,
      cv.meaning,
      "",
      ""
    ]);
  });
  sheetVocab.getRange(sheetVocab.getLastRow() + 1, 1, vocabRows.length, 7).setValues(vocabRows);

  // 3. 寫入 Sentences
  const sheetSentences = ss.getSheetByName("Sentences");
  const sentenceRows = [];
  generated.sentences.forEach((s, idx) => {
    sentenceRows.push([upcomingIssue.code, idx + 1, s.thai, s.phonetic, s.meaning]);
  });
  sheetSentences.getRange(sheetSentences.getLastRow() + 1, 1, sentenceRows.length, 5).setValues(sentenceRows);

  // 4. 寫入 Grammar
  const sheetGrammar = ss.getSheetByName("Grammar");
  const grammarRows = [];
  generated.grammar.forEach((g, idx) => {
    grammarRows.push([upcomingIssue.code, idx + 1, g.title, g.explanation, JSON.stringify(g.examples)]);
  });
  sheetGrammar.getRange(sheetGrammar.getLastRow() + 1, 1, grammarRows.length, 5).setValues(grammarRows);

  // 5. 新增下下一期 upcoming 列
  if (generated.next_issue) {
    sheetIssues.appendRow([
      generated.next_issue.code,
      "2026",
      generated.next_issue.code.split("w")[1] || "45",
      generated.next_issue.date,
      "upcoming",
      generated.next_issue.title,
      generated.next_issue.desc,
      "", "約 10 分鐘", "", "", "", "", "", "", ""
    ]);
  }

  // 6. 寄發專屬問候信
  const issueInfo = {
    issue_code: upcomingIssue.code,
    title: generated.issue_title,
    subtitle_1: generated.subtitle_part_1,
    subtitle_2: generated.subtitle_part_2,
    email_subject: generated.email.subject_line,
    email_intro_html: generated.email.intro_text,
    email_highlights_html: generated.email.highlights.map(h => '<div class="highlight-item">' + h + '</div>').join("\n")
  };

  RECIPIENTS.forEach(r => {
    sendPersonalizedEmail(r, issueInfo);
  });

  return { status: "success", published: upcomingIssue.code };
}

/**
 * 呼叫 Gemini API 產出教材 JSON
 */
function callGeminiGenerate(upcomingIssue) {
  const apiKey = getApiKey();
  const models = ["gemini-3.5-flash-lite", "gemini-3.8-flash"];
  
  const prompt = `
你是一位深諳泰語教學法與觀光文化底蘊的頂級泰語教育專家，請為「Thai_Weekly（泰語學習週報）」編纂本期（VOL. ${upcomingIssue.code}）的完整教材內容。
【本期主題】：${upcomingIssue.title}
【主題簡介】：${upcomingIssue.desc}
【目標受眾】：台灣商務人士、自由行旅客、觀光旅遊從業人員。
【文字規範】：必須嚴格使用「台灣繁體中文」，絕對嚴禁出現任何簡體字！
【說文解字・詞彙拆解全自動辨識規範】：請針對 vocab 陣列中每個單字進行構詞結構判斷：
  1. 【複合詞與實用片語必須拆解】：凡是由兩個以上具獨立意義之詞素組成的複合詞、動賓短語、偏正詞組（如：ห้องเตียงเดี่ยว、แอร์ไม่เย็น、น้ำไม่ร้อน、เปลี่ยนห้อง、ยาแก้ปวด、คืนภาษี、อาหารทะเล、ลูกค้า、สนามบิน、ใบเสร็จ 等），必須輸出：
     - breakdown：拆解各詞素結構，為包含 thai, phonetic, meaning 的物件陣列（例如 ยาแก้ปวด 拆解為 ยา[藥] + แก้[解/止] + ปวด[疼痛]）。
     - extensions：2~3 個同字根之實用高頻派生詞（包含 thai, phonetic, meaning）。
  2. 【純外來語與單一字根嚴禁拆解】：純音譯外來語（如 คีย์การ์ด Key card、มิเตอร์ Meter）或單一獨立字根詞（如 แพ้、นวด、เบา、แรง），breakdown 與 extensions 一律回傳空陣列 []。

請直接回傳合法的 JSON 格式，不要包含額外文字：
{
  "issue_code": "${upcomingIssue.code}",
  "issue_title": "${upcomingIssue.title}",
  "subtitle_part_1": "副標題前半段",
  "subtitle_part_2": "副標題後半段",
  "issue_desc": "本期重點概述",
  "highlights_summary": "9個核心單字 ｜ 5組實用對話句型 ｜ 2大核心語法 ｜ 深度文化專題與單字發音",
  "read_time_minutes": "10",
  "vocab": [
    {
      "thai": "泰文",
      "phonetic": "拼音",
      "pos": "[動詞]",
      "meaning": "繁中釋義",
      "breakdown": [
        {"thai": "字根", "phonetic": "拼音", "meaning": "字義"}
      ],
      "extensions": [
        {"thai": "延伸衍生詞", "phonetic": "拼音", "meaning": "繁中釋義"}
      ]
    }
  ],
  "sentences": [
    {"thai": "泰文句子", "phonetic": "拼音", "meaning": "繁中翻譯"}
  ],
  "grammar": [
    {
      "title": "語法標題",
      "explanation": "解析說明",
      "examples": [
        {"thai": "泰文例句", "phonetic": "拼音", "meaning": "中文"}
      ]
    }
  ],
  "culture": {
    "title": "文化專題標題",
    "paragraphs": ["第1段", "第2段", "第3段"],
    "callout": "線控經理實務備忘（Tour Product Manager Memo）",
    "vocab_items": [
      {"thai": "泰文詞", "phonetic": "拼音", "meaning": "中文釋義"}
    ]
  },
  "email": {
    "subject_line": "【泰語學習週報】VOL. ${upcomingIssue.code} ｜ 主旨",
    "intro_text": "開場導言（HTML 換行以 <br><br> 分隔）",
    "highlights": [
      "1. 亮點一",
      "2. 亮點二",
      "3. 亮點三"
    ]
  },
  "next_issue": {
    "code": "26w45",
    "date": "2026-11-07",
    "title": "下週預告標題",
    "desc": "下週預告簡介"
  }
}
`;

  for (let i = 0; i < models.length; i++) {
    const model = models[i];
    const url = "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent?key=" + apiKey;
    const payload = {
      contents: [{ parts: [{ text: prompt }] }],
      generationConfig: {
        responseMimeType: "application/json",
        temperature: 0.7
      }
    };

    try {
      const resp = UrlFetchApp.fetch(url, {
        method: "post",
        contentType: "application/json",
        payload: JSON.stringify(payload),
        muteHttpExceptions: true
      });

      if (resp.getResponseCode() === 200) {
        const json = JSON.parse(resp.getContentText());
        let text = json.candidates[0].content.parts[0].text.trim();
        if (text.startsWith("```")) {
          text = text.replace(/^```[a-zA-Z]*\n/, "").replace(/\n```$/, "");
        }
        return JSON.parse(text);
      }
    } catch (e) {
      Logger.log("Model " + model + " 失敗: " + e);
    }
  }

  throw new Error("Gemini 模型生成失敗，請檢查 API Key！");
}

/**
 * 清理 Issues 工作表中已存在的 memo 重複標題前綴
 */
function cleanExistingMemos() {
  const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  const sheet = ss.getSheetByName("Issues");
  const data = sheet.getDataRange().getValues();
  let updatedCount = 0;
  for (let i = 1; i < data.length; i++) {
    let memo = String(data[i][12] || "");
    if (memo) {
      let cleaned = memo.replace(/^(<b>)?\s*💡?\s*線控經理實務備忘[（(][^）)]*[）)][:：]?\s*(<\/b>)?\s*(<br\s*\/?>)?/i, "").trim();
      if (cleaned !== memo) {
        sheet.getRange(i + 1, 13).setValue(cleaned);
        updatedCount++;
      }
    }
  }
  Logger.log("已清理備忘數量: " + updatedCount);
  return { status: "success", updatedCount: updatedCount };
}
/**
 * 試算表選單觸發的自動補齊歷史單字說文解字入口
 */
function menuBackfillAnatomy() {
  let issueCode = null;
  if (SpreadsheetApp.getUi) {
    try {
      const ui = SpreadsheetApp.getUi();
      const resp = ui.prompt(
        "自動補齊歷史單字說文解字 (Auto-Backfill)",
        "請輸入欲補齊的期數代碼（如 26w43），若留空則自動檢查並補齊所有已發布期數缺漏之複合詞：",
        ui.ButtonSet.OK_CANCEL
      );
      if (resp.getSelectedButton() === ui.Button.OK) {
        issueCode = resp.getResponseText().trim() || null;
      } else {
        return;
      }
    } catch (e) {
      Logger.log("非 UI 執行環境: " + e);
    }
  }
  const result = backfillAnatomyForIssue(issueCode);
  if (SpreadsheetApp.getUi) {
    try {
      SpreadsheetApp.getUi().alert(
        "回填完成",
        "處理狀態: " + result.status + "\n成功回填單字數量: " + (result.updatedCount || 0) + "\n" + (result.msg || ""),
        SpreadsheetApp.getUi().ButtonSet.OK
      );
    } catch (e) {}
  }
  return result;
}

/**
 * 自動抓取缺少說文解字之單字，呼叫 Gemini API 智慧辨識複合詞結構並自動回填回 Google Sheet
 * @param {string|null} issueCode 指定期數（如 '26w43'），未指定則檢查全體已發布期數
 */
function backfillAnatomyForIssue(issueCode) {
  const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  const sheetVocab = ss.getSheetByName("Vocab");
  if (!sheetVocab) {
    return { status: "error", msg: "找不到 Vocab 工作表" };
  }

  // 確保 F1:G1 標頭存在
  if (!sheetVocab.getRange(1, 6).getValue()) {
    sheetVocab.getRange(1, 6, 1, 2).setValues([["breakdown_json", "extensions_json"]]);
  }

  const data = sheetVocab.getDataRange().getValues();
  const pendingItems = [];

  for (let i = 1; i < data.length; i++) {
    const rowIssue = String(data[i][0]).trim();
    const type = String(data[i][1]).trim();
    const thai = String(data[i][2]).trim();
    const phonetic = String(data[i][3]).trim();
    const meaning = String(data[i][4]).trim();
    const breakdownJson = String(data[i][5] || "").trim();

    // 僅處理指定期數（若未指定則處理所有期數之核心單字）
    if (issueCode && rowIssue !== issueCode) continue;
    if (type !== "core") continue;

    // 若 breakdown_json 已有合法內容（非空且非 []），則跳過
    if (breakdownJson && breakdownJson !== "[]") continue;

    pendingItems.push({
      rowIndex: i + 1,
      issue_code: rowIssue,
      thai: thai,
      phonetic: phonetic,
      meaning: meaning
    });
  }

  if (pendingItems.length === 0) {
    Logger.log("無缺少說文解字之單字需要回填。");
    return { status: "success", msg: "所有核心單字均已完成拆解或已填妥", updatedCount: 0 };
  }

  Logger.log("待呼叫 Gemini 分析拆解之單字數量: " + pendingItems.length);

  // 批次呼叫 Gemini 解析
  const analysisResults = callGeminiBatchAnatomy(pendingItems);
  let updatedCount = 0;

  pendingItems.forEach(item => {
    const res = analysisResults[item.thai];
    if (res) {
      const breakdownStr = (Array.isArray(res.breakdown) && res.breakdown.length > 0) ? JSON.stringify(res.breakdown) : "";
      const extensionsStr = (Array.isArray(res.extensions) && res.extensions.length > 0) ? JSON.stringify(res.extensions) : "";
      sheetVocab.getRange(item.rowIndex, 6, 1, 2).setValues([[breakdownStr, extensionsStr]]);
      if (breakdownStr) updatedCount++;
    }
  });

  SpreadsheetApp.flush();
  Logger.log("回填完成！成功寫入複合詞拆解數量: " + updatedCount);
  return {
    status: "success",
    processedCount: pendingItems.length,
    updatedCount: updatedCount,
    keys: Object.keys(analysisResults),
    msg: "已分析 " + pendingItems.length + " 個單字，成功寫入 " + updatedCount + " 組複合詞拆解資料！"
  };
}

/**
 * 批次呼叫 Gemini 分析複合詞構詞結構
 */
function callGeminiBatchAnatomy(vocabItems) {
  const apiKey = getApiKey();
  const models = ["gemini-3.5-flash-lite", "gemini-3.8-flash"];
  let lastErr = "";

  const prompt = `
你是一位深諳泰語構詞學的資深教育語言學家。請針對以下清單中的泰語單字進行【說文解字・詞彙拆解構詞分析】。

【嚴格規則】：
1. 【複合詞與實用片語必須拆解】：
   - 凡由兩個以上具獨立意義之詞素組合而成的複合詞、動賓片語、偏正結構（例如：ห้องเตียงเดี่ยว, แอร์ไม่เย็น, น้ำไม่ร้อน, เปลี่ยนห้อง, ยาแก้ปวด, คืนภาษี, อาหารทะเล, ลูกค้า, สนามบิน, ใบเสร็จ 等）。
   - 必須輸出 breakdown 陣列：包含各組成詞素之 thai, phonetic, meaning（繁體中文釋義）。
   - 必須輸出 extensions 陣列：2~3 個同字根之高頻實用衍生詞（包含 thai, phonetic, meaning）。
2. 【純音譯外來語與單一字根嚴禁拆解】：
   - 純外來語音譯詞（如 คีย์การ์ด Key card, มิเตอร์ Meter）或單一字根詞（如 แพ้, นวด, เบา, แรง），其 breakdown 與 extensions 一律填入空陣列 []。
3. 【文字規範】：必須嚴格使用「台灣繁體中文」，嚴禁使用簡體字！

【待分析單字清單】：
${JSON.stringify(vocabItems.map(v => ({ thai: v.thai, phonetic: v.phonetic, meaning: v.meaning })), null, 2)}

請直接回傳合法的 JSON 物件（Key 為單字的泰文），格式如下：
{
  "單字泰文": {
    "breakdown": [
      {"thai": "詞素", "phonetic": "拼音", "meaning": "字義"}
    ],
    "extensions": [
      {"thai": "衍生詞", "phonetic": "拼音", "meaning": "釋義"}
    ]
  }
}
`;

  for (let i = 0; i < models.length; i++) {
    const model = models[i];
    const url = "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent?key=" + apiKey;
    const payload = {
      contents: [{ parts: [{ text: prompt }] }],
      generationConfig: {
        responseMimeType: "application/json",
        temperature: 0.2
      }
    };

    try {
      const resp = UrlFetchApp.fetch(url, {
        method: "post",
        contentType: "application/json",
        payload: JSON.stringify(payload),
        muteHttpExceptions: true
      });

      if (resp.getResponseCode() === 200) {
        const json = JSON.parse(resp.getContentText());
        let t = json.candidates[0].content.parts[0].text.trim();
        if (t.startsWith("```")) {
          t = t.replace(/^```[a-zA-Z]*\n/, "").replace(/\n```$/, "");
        }
        return JSON.parse(t);
      } else {
        lastErr = "HTTP " + resp.getResponseCode() + ": " + resp.getContentText();
        Logger.log("Batch Anatomy Model " + model + " 回應異常: " + lastErr);
      }
    } catch (e) {
      lastErr = String(e);
      Logger.log("Batch Anatomy Model " + model + " 失敗: " + e);
    }
  }

  throw new Error("Gemini 批次說文解字分析失敗: " + lastErr);
}
