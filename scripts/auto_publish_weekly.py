#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auto_publish_weekly.py

Thai_Weekly (泰語學習週報) 原地一條龍全自動化發布與寄信系統
- 呼叫 Google Gemini API 產出當週結構化泰語教學內容 (嚴格台灣繁體中文)
- 套用 templates/lesson_template.html 產生 YYwWW.html
- 自動更新 index.html (Spotlight Hero, 近期特輯, 歷史手風琴抽屜與下期預告)
- 生成 email_YYwWW.html 專屬皇室紫金 HTML 電子報
- 驗證 GitHub Pages 網址非 404 (HTTP 200 OK 防呆)
- 透過 Gmail SMTP 分別獨立發送 3 封一對一專屬問候信件
"""

import os
import sys
import re
import json
import time
import argparse
import datetime
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
import requests

# 專案路徑設定
ROOT_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = ROOT_DIR / "templates"
LESSON_TEMPLATE_PATH = TEMPLATES_DIR / "lesson_template.html"
INDEX_PATH = ROOT_DIR / "index.html"

# 收件人清單：(代稱/稱謂, Email, 問候語)
RECIPIENTS = [
    ("Martin", "voyager.martin@gmail.com", "早安 Martin！"),
    ("Annie", "anniechen0209@gmail.com", "早安 Annie！"),
    ("昌哥", "tienzitw@yahoo.com.tw", "早安 昌哥！"),
]

# 模型候選清單（自動降級容錯）
GEMINI_MODELS = [
    "gemini-flash-latest",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
]


def get_current_issue_meta(target_issue=None):
    """計算本週與下週的期數、日期等中繼資料"""
    now = datetime.datetime.now()
    if target_issue:
        # 自訂期數格式 YYwWW
        match = re.match(r"(\d{2})w(\d{2})", target_issue)
        if match:
            year_short, week_num = match.groups()
            year = 2000 + int(year_short)
            week = int(week_num)
        else:
            raise ValueError(f"無效的期數格式: {target_issue}，應為如 26w44")
    else:
        year, week, _ = now.isocalendar()
        year_short = str(year)[-2:]
    
    issue_code = f"{year_short}w{week:02d}"
    
    # 計算本週六與下週六日期
    # 若當天不是週六，計算當週週六或使用今天
    days_until_saturday = (5 - now.weekday()) % 7
    saturday_date = now + datetime.timedelta(days=days_until_saturday)
    issue_date_str = saturday_date.strftime("%Y-%m-%d")
    
    next_week = week + 1
    next_year_short = year_short
    if next_week > 52:
        next_week = 1
        next_year_short = str(int(year_short) + 1).zfill(2)
    next_issue_code = f"{next_year_short}w{next_week:02d}"
    next_saturday = saturday_date + datetime.timedelta(days=7)
    next_date_str = next_saturday.strftime("%Y-%m-%d")
    
    return {
        "year": str(year),
        "year_short": year_short,
        "week": str(week),
        "week_zfill": str(week).zfill(2),
        "issue_code": issue_code,
        "issue_date": issue_date_str,
        "next_issue_code": next_issue_code,
        "next_issue_date": next_date_str,
    }


def extract_upcoming_from_index():
    """從現有 index.html 中讀取預告卡片的主題與說明"""
    if not INDEX_PATH.exists():
        return None
    
    content = INDEX_PATH.read_text(encoding="utf-8")
    
    # 搜尋即將推出的卡片
    match = re.search(
        r'class="issue-card"[^>]*style="[^"]*opacity:[^"]*"[^>]*data-code="([^"]+)"[^>]*data-title="([^"]+)"[^>]*data-desc="([^"]+)"[^>]*data-tags="([^"]*)"',
        content,
    )
    if match:
        return {
            "code": match.group(1),
            "title": match.group(2),
            "desc": match.group(3),
            "tags": match.group(4),
        }
    
    # 次要匹配方式
    match2 = re.search(
        r'data-code="([^"]+)"[^>]*data-title="([^"]+)"[^>]*data-desc="([^"]+)"',
        content,
    )
    if match2:
        return {
            "code": match2.group(1),
            "title": match2.group(2),
            "desc": match2.group(3),
            "tags": "",
        }
    
    return None


def call_gemini_api(prompt, api_key):
    """呼叫 Gemini API 並具備自動備援模型切換"""
    # 優先嘗試 google-genai SDK
    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=api_key)
        for model in GEMINI_MODELS:
            print(f"[INFO] 嘗試使用 google-genai 呼叫模型: {model}...")
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.7,
                    ),
                )
                if response and response.text:
                    return response.text
            except Exception as e:
                print(f"[WARN] 模型 {model} 呼叫失敗 ({e})，嘗試下一個備援模型...")
    except ImportError:
        print("[INFO] 未安裝 google-genai 套件，改用 REST API 呼叫...")

    # REST API 備援方案
    for model in GEMINI_MODELS:
        print(f"[INFO] 嘗試使用 REST API 呼叫模型: {model}...")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.7,
            },
        }
        try:
            resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=120)
            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return text
            else:
                print(f"[WARN] REST API 模型 {model} 回傳 {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            print(f"[WARN] REST API 呼叫 {model} 發生例外: {e}")
            time.sleep(2)

    raise RuntimeError("所有 Gemini 備援模型皆呼叫失敗，請檢查 API Key 或網路連線！")


def generate_lesson_content(issue_meta, upcoming_info, api_key):
    """組裝 Prompt 並呼叫 Gemini 產出符合規範的教學 JSON 結構"""
    issue_code = upcoming_info["code"] if upcoming_info else issue_meta["issue_code"]
    planned_title = upcoming_info["title"] if upcoming_info else "觀光實務與日常生活泰語"
    planned_desc = upcoming_info["desc"] if upcoming_info else "精選實用詞彙與語法拆解"

    prompt = f"""
你是一位深諳泰語教學法與觀光文化底蘊的頂級泰語教育專家（Gemini Spark），請為「Thai_Weekly（泰語學習週報）」編纂本期（VOL. {issue_code}）的完整教材內容。

【本期主題】：{planned_title}
【主題簡介】：{planned_desc}
【出刊日期】：{issue_meta['issue_date']} (週六)
【目標受眾】：台灣商務人士、自由行旅客、觀光旅遊從業人員（領隊、線控經理）。
【文字規範】：必須嚴格使用「台灣繁體中文」（繁體字），絕對嚴禁出現任何簡體字！

請直接回傳合法的 JSON 格式，不要包含額外的說明文字，JSON 結構嚴格要求如下：
{{
  "issue_code": "{issue_code}",
  "issue_title": "{planned_title}",
  "subtitle_part_1": "副標題前半段（如：專為星級飯店接待與旅宿實務打造。）",
  "subtitle_part_2": "副標題後半段（如：解析狀態存留助詞與委婉溝通結構，深入泰式款待禮儀與小費文化。）",
  "issue_desc": "大約 80-120 字的本期亮點完整概述，用於首頁 Spotlight Hero 與搜尋卡片。",
  "highlights_summary": "9個核心單字 ｜ 5組實用對話句型 ｜ 2大核心語法 ｜ 深度文化專題與單字發音",
  "read_time_minutes": "10",
  "search_tags": "以空格分隔的搜尋關鍵字（包含主題、核心泰文單字、語法、文化詞）",
  
  "vocab": [
    // 嚴格產出剛好 9 個核心高頻實務單字
    {{
      "thai": "泰文字詞",
      "phonetic": "RTGS或國際音標發音標記",
      "pos": "[詞性，如 [名詞]、[動詞]、[片語]]",
      "meaning": "台灣繁體中文釋義，包含實務情境備註或易混淆說明"
    }}
  ],

  "sentences": [
    // 嚴格產出剛好 5 組實用對話句型
    {{
      "thai": "泰文句子（句尾需得體搭配ครับ/ค่ะ）",
      "phonetic": "羅馬拼音讀音",
      "meaning": "台灣繁體中文翻譯與實用語境提示"
    }}
  ],

  "grammar": [
    // 嚴格產出 2 個核心語法解析點
    {{
      "title": "語法重點 1 標題",
      "explanation": "語法公式與深入剖析（包含結構公式、語氣特點、商務或日常應用說明）",
      "examples": [
        // 剛好 3 個搭配例句
        {{
          "thai": "泰文搭配詞句",
          "phonetic": "拼音",
          "meaning": "中文意思說明"
        }}
      ]
    }},
    {{
      "title": "語法重點 2 標題",
      "explanation": "語法公式與深入剖析",
      "examples": [
        // 剛好 3 個搭配例句
        {{
          "thai": "泰文搭配詞句",
          "phonetic": "拼音",
          "meaning": "中文意思說明"
        }}
      ]
    }}
  ],

  "culture": {{
    "title": "文化專題標題（如：泰式款待哲學與星級飯店小費禮儀誌）",
    "paragraphs": [
      "深度文化隨筆第 1 段（探討社會心理、文化哲學，如 ใจเย็นๆ 或 เกรงใจ 等處事基因）",
      "深度文化隨筆第 2 段（實務情境應對、避雷破局點）",
      "深度文化隨筆第 3 段（相關風俗禮儀或文化細節）"
    ],
    "callout": "線控經理實務備忘（Line Control Tourism Memo）：針對該主題提出極具同業實務價值的避坑指南或專業防呆法則。",
    "vocab_items": [
      // 嚴格產出 8 組文化專題關鍵精選語彙（供原地標準語音發音使用）
      {{
        "thai": "泰文文化詞",
        "phonetic": "拼音",
        "meaning": "中文釋義與文化寓意說明"
      }}
    ]
  }},

  "email": {{
    "subject_line": "【泰語學習週報】VOL. {issue_code} ｜ 吸睛的電子報主旨",
    "intro_text": "2 段充滿旅遊臨場感與人文溫度的開場白導言（約 150-200 字，HTML 換行以 <br><br> 分隔）",
    "highlights": [
      "1. 亮點一（單字庫特色）",
      "2. 亮點二（語法思維破局點）",
      "3. 亮點三（文化專題與單字發音特色）"
    ]
  }},

  "next_issue": {{
    "code": "{issue_meta['next_issue_code']}",
    "date": "{issue_meta['next_issue_date']}",
    "title": "構思下一期（{issue_meta['next_issue_code']}）的吸睛主題（例如：《週末市集跳蚤尋寶・手作工藝與殺價議價實務》）",
    "desc": "下一期預計涵蓋的重點預告（約 40-60 字）",
    "tags": "下一期的搜尋關鍵字"
  }}
}}
"""
    print("[INFO] 正在呼叫 Gemini API 產出本週教材 JSON 結構...")
    raw_response = call_gemini_api(prompt, api_key)
    
    # 清理 markdown codeblock
    clean_json = raw_response.strip()
    if clean_json.startswith("```"):
        clean_json = re.sub(r"^```[a-zA-Z]*\n", "", clean_json)
        clean_json = re.sub(r"\n```$", "", clean_json)
    
    data = json.loads(clean_json)
    return data


def render_lesson_html(data, issue_meta):
    """讀取 lesson_template.html 並填入當週產出內容"""
    if not LESSON_TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"找不到基礎模板: {LESSON_TEMPLATE_PATH}")
    
    template = LESSON_TEMPLATE_PATH.read_text(encoding="utf-8")
    
    # 1. 產生 Vocab Cards HTML
    vocab_html_list = []
    for item in data["vocab"]:
        card = f"""      <div class="vocab-card">
        <div class="vocab-top">
          <div>
            <div class="thai-word">{item['thai']}</div>
            <div class="phonetic">{item['phonetic']}</div>
          </div>
          <button class="btn-audio" onclick="playTTS('{item['thai']}', this)" title="播放泰語標準發音">🔊</button>
        </div>
        <div class="meaning">{item.get('pos', '')} {item['meaning']}</div>
      </div>"""
        vocab_html_list.append(card)
    vocab_section_html = "\n".join(vocab_html_list)

    # 2. 產生 Sentences HTML
    sentence_html_list = []
    for item in data["sentences"]:
        card = f"""    <div class="sentence-card">
      <div>
        <div class="sentence-thai">{item['thai']}</div>
        <div class="sentence-phonetic">{item['phonetic']}</div>
        <div class="sentence-meaning">{item['meaning']}</div>
      </div>
      <button class="btn-audio" onclick="playTTS('{item['thai']}', this)" title="播放例句發音">🔊</button>
    </div>"""
        sentence_html_list.append(card)
    sentences_section_html = "\n".join(sentence_html_list)

    # 3. 產生 Grammar HTML
    grammar_html_list = []
    for idx, item in enumerate(data["grammar"], start=1):
        pills_list = []
        for eg in item["examples"]:
            pill = f"""        <div class="example-pill">
          <span class="th">{eg['thai']}</span>
          <span style="color:#cbd5e1;">({eg['phonetic']}) {eg['meaning']}</span>
          <button class="btn-audio-mini" onclick="playTTS('{eg['thai']}', this)" title="播放發音">🔊</button>
        </div>"""
            pills_list.append(pill)
        pills_html = "\n".join(pills_list)

        card = f"""    <div class="grammar-card">
      <div class="grammar-card-title">💡 語法重點 {idx}：{item['title']}</div>
      <p style="color:#d1d5db; line-height:1.75;">
        {item['explanation']}
      </p>
      
      <div class="grammar-sub">常用搭配例句：</div>
      <div class="pill-group">
{pills_html}
      </div>
    </div>"""
        grammar_html_list.append(card)
    grammar_section_html = "\n".join(grammar_html_list)

    # 4. 產生 Culture HTML (含 8 組文化專題發音語彙)
    culture_paras = "\n".join([f"      <p style='margin-top:14px;'>{p}</p>" for p in data["culture"]["paragraphs"]])
    
    cult_vocab_pills = []
    for cv in data["culture"]["vocab_items"]:
        pill = f"""          <div class="example-pill">
            <span class="th">{cv['thai']}</span>
            <span style="color:#cbd5e1;">({cv['phonetic']}) {cv['meaning']}</span>
            <button class="btn-audio-mini" onclick="playTTS('{cv['thai']}', this)" title="播放發音">🔊</button>
          </div>"""
        cult_vocab_pills.append(pill)
    cult_vocab_html = "\n".join(cult_vocab_pills)

    # 清理 callout 避免模型自帶前綴與模板重複
    clean_callout = data['culture']['callout'].strip()
    clean_callout = re.sub(r'^(<b>)?\s*💡?\s*線控經理實務備忘[（(][^）)]*[）)][:：]?\s*(</b>)?\s*(<br\s*/?>)?', '', clean_callout, flags=re.I).strip()

    culture_section_html = f"""    <div class="culture-card">
      <h3>🏛️ {data['culture']['title']}</h3>
{culture_paras}
      
      <div class="culture-callout">
        <b>💡 線控經理實務備忘（Line Control Tourism Memo）：</b><br>
        {clean_callout}
      </div>

      <!-- 🏮 文化專題關鍵字庫（點擊播放原地標準語音） -->
      <div class="culture-vocab-sec" style="margin-top: 24px; border-top: 1px solid rgba(245, 158, 11, 0.25); padding-top: 20px;">
        <div style="font-size: 17px; font-weight: 700; color: var(--accent-gold); margin-bottom: 14px; display: flex; align-items: center; gap: 8px;">
          <span>🎧</span> 文化專題精選語彙（點擊按鈕聆聽標準泰語發音）：
        </div>
        <div class="pill-group">
{cult_vocab_html}
        </div>
      </div>
    </div>"""

    # 5. 替換模板標記
    rendered = template
    rendered = rendered.replace("{{ISSUE_CODE}}", data["issue_code"])
    rendered = rendered.replace("{{ISSUE_TITLE}}", data["issue_title"])
    rendered = rendered.replace("{{ISSUE_YEAR}}", issue_meta["year"])
    rendered = rendered.replace("{{ISSUE_WEEK}}", issue_meta["week"])
    rendered = rendered.replace("{{ISSUE_DATE}}", issue_meta["issue_date"])
    rendered = rendered.replace("{{SUBTITLE_PART_1}}", data.get("subtitle_part_1", ""))
    rendered = rendered.replace("{{SUBTITLE_PART_2}}", data.get("subtitle_part_2", ""))
    rendered = rendered.replace("{{READ_TIME}}", data.get("read_time_minutes", "10"))
    rendered = rendered.replace("{{HIGHLIGHTS}}", data.get("highlights_summary", ""))

    # 替換 Section 內容
    # 替換 vocab-grid
    rendered = re.sub(
        r'<div class="vocab-grid">[\s\S]*?</div>\s*</section>',
        f'<div class="vocab-grid">\n{vocab_section_html}\n    </div>\n  </section>',
        rendered,
        count=1,
    )
    # 替換 sentences section
    rendered = re.sub(
        r'<div class="sec-tag">對話實戰</div>\s*</div>[\s\S]*?</section>',
        f'<div class="sec-tag">對話實戰</div>\n    </div>\n{sentences_section_html}\n  </section>',
        rendered,
        count=1,
    )
    # 替換 grammar section
    rendered = re.sub(
        r'<div class="sec-tag">文法剖析</div>\s*</div>[\s\S]*?</section>',
        f'<div class="sec-tag">文法剖析</div>\n    </div>\n{grammar_section_html}\n  </section>',
        rendered,
        count=1,
    )
    # 替換 culture section
    rendered = re.sub(
        r'<div class="sec-tag">人文背景</div>\s*</div>[\s\S]*?</section>',
        f'<div class="sec-tag">人文背景</div>\n    </div>\n{culture_section_html}\n  </section>',
        rendered,
        count=1,
    )

    out_file = ROOT_DIR / f"{data['issue_code']}.html"
    out_file.write_text(rendered, encoding="utf-8")
    print(f"[SUCCESS] 成功生成當週課程頁面: {out_file.name}")
    return out_file


def render_email_html(data, issue_meta):
    """產生當週的皇室紫金 HTML 電子報（保留 {{RECIPIENT_NAME}} 變數）"""
    highlights_html = "".join([f'<div class="highlight-item">{h}</div>\n' for h in data["email"]["highlights"]])
    
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0d0814; color: #f8fafc; margin: 0; padding: 24px; }}
  .email-container {{ max-width: 640px; margin: 0 auto; background: #170f24; border: 1px solid #443063; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
  .header {{ background: linear-gradient(135deg, #231738 0%, #3b1d61 100%); padding: 32px 28px; border-bottom: 2px solid #f59e0b; }}
  .tag {{ display: inline-block; background: rgba(245, 158, 11, 0.2); color: #fde68a; border: 1px solid #f59e0b; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 700; letter-spacing: 0.5px; margin-bottom: 12px; }}
  .title {{ color: #ffffff; font-size: 24px; font-weight: 800; margin: 0 0 8px 0; line-height: 1.35; }}
  .subtitle {{ color: #cbd5e1; font-size: 15px; margin: 0; line-height: 1.6; }}
  .content {{ padding: 28px; }}
  .greeting {{ font-size: 17px; font-weight: 700; color: #fde68a; margin-bottom: 16px; }}
  .intro-text {{ font-size: 15.5px; line-height: 1.8; color: #e2e8f0; margin-bottom: 24px; }}
  .highlight-card {{ background: #231738; border: 1px solid #443063; border-left: 4px solid #f59e0b; border-radius: 10px; padding: 18px 20px; margin-bottom: 24px; }}
  .highlight-title {{ font-size: 16px; font-weight: 700; color: #fde047; margin-bottom: 12px; }}
  .highlight-item {{ font-size: 14.5px; line-height: 1.7; color: #cbd5e1; margin-bottom: 10px; }}
  .highlight-item:last-child {{ margin-bottom: 0; }}
  .btn-wrapper {{ text-align: center; margin: 32px 0 24px 0; }}
  .btn-cta {{ display: inline-block; background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: #0d0814 !important; font-size: 16px; font-weight: 800; text-decoration: none; padding: 14px 32px; border-radius: 30px; box-shadow: 0 4px 18px rgba(245, 158, 11, 0.35); }}
  .footer {{ background: #0f0a18; padding: 20px 28px; text-align: center; border-top: 1px solid #231738; font-size: 13px; color: #a78bfa; line-height: 1.6; }}
  .footer a {{ color: #fde68a; text-decoration: none; }}
</style>
</head>
<body>
<div class="email-container">
  <div class="header">
    <div class="tag">VOL. {data['issue_code']} ｜ {issue_meta['issue_date']} 泰國皇室紫金特輯</div>
    <h1 class="title">{data['issue_title']}</h1>
    <p class="subtitle">{data.get('subtitle_part_1', '')} {data.get('subtitle_part_2', '')}</p>
  </div>
  
  <div class="content">
    <div class="greeting">早安 {{{{RECIPIENT_NAME}}}}！</div>
    
    <div class="intro-text">
      {data['email']['intro_text']}
    </div>

    <div class="highlight-card">
      <div class="highlight-title">✨ 本期三大核心專欄亮點</div>
{highlights_html}
    </div>

    <div class="btn-wrapper">
      <a href="https://voyagermartin.github.io/Thai_Weekly/{data['issue_code']}.html" class="btn-cta">
        👉 點此前往 {data['issue_code']} 線上數位雜誌特輯
      </a>
      <div style="font-size: 13px; color: #a78bfa; margin-top: 10px;">
        💡 支援網頁原地 1.0x / 0.75x 雙引擎語音播放、文化單字發音與卡片遮蔽記憶測驗
      </div>
    </div>
  </div>

  <div class="footer">
    泰語學習週報｜全期索引門戶：<a href="https://voyagermartin.github.io/Thai_Weekly/index.html">voyagermartin.github.io/Thai_Weekly</a><br>
    由 GitHub Actions 全自動排程出刊 ｜ 敬祝閱讀愉快，週末充實順遂！
  </div>
</div>
</body>
</html>
"""
    out_file = ROOT_DIR / f"email_{data['issue_code']}.html"
    out_file.write_text(html, encoding="utf-8")
    print(f"[SUCCESS] 成功生成電子報模板: {out_file.name}")
    return out_file


def update_index_html(data, issue_meta):
    """更新 index.html 的導航、Spotlight Hero、近期特輯、下期預告與歷史歸檔手風琴"""
    if not INDEX_PATH.exists():
        raise FileNotFoundError(f"找不到首頁: {INDEX_PATH}")
    
    content = INDEX_PATH.read_text(encoding="utf-8")
    code = data["issue_code"]
    title = data["issue_title"]
    desc = data["issue_desc"]
    date_str = issue_meta["issue_date"]
    next_info = data["next_issue"]

    # 1. 更新導航列按鈕
    content = re.sub(
        r'<a href="[^"]+\.html" class="nav-btn">📖 最新刊 [^<]+</a>',
        f'<a href="{code}.html" class="nav-btn">📖 最新刊 {code}</a>',
        content,
    )

    # 2. 更新 Spotlight Hero
    spotlight_replacement = f"""  <!-- 2. 方案 1 核心：本週最新刊置頂大封面 (Spotlight Hero) -->
  <div class="spotlight-hero">
    <div>
      <div class="spotlight-badge-row">
        <span class="spotlight-tag-live">● 本週最新刊 ｜ VOL. {code}</span>
        <span class="spotlight-date">{date_str} SATURDAY</span>
      </div>
      <h1 class="spotlight-title">{title}</h1>
      <p class="spotlight-desc">
        {desc}
      </p>
    </div>
    
    <div class="spotlight-footer">
      <div class="spotlight-pills">
        <span class="spotlight-pill">🎯 9 個核心單字</span>
        <span class="spotlight-pill">💬 5 組情境對話句型</span>
        <span class="spotlight-pill">🔊 含文化單字雙引擎發音</span>
        <span class="spotlight-pill">👁️ 遮蔽記憶自測</span>
      </div>
      <a href="{code}.html" class="btn-enter-primary">進入 {code} 課程 →</a>
    </div>
  </div>"""

    content = re.sub(
        r'<!-- 2\. 方案 1 核心：本週最新刊置頂大封面 \(Spotlight Hero\) -->[\s\S]*?</div>\s*</div>',
        spotlight_replacement,
        content,
        count=1,
    )

    # 3. 在 #recent-grid 開頭插入新卡片
    new_recent_card = f"""    <!-- Issue {code} Card (Current Issue) -->
    <a 
      href="{code}.html" 
      class="issue-card" 
      data-code="{code}" 
      data-title="{title}" 
      data-desc="{desc}"
      data-tags="{data.get('search_tags', '')}"
    >
      <div>
        <span class="issue-badge" style="background: rgba(245, 158, 11, 0.2); color: #fde68a; border-color: rgba(245, 158, 11, 0.4);">{code} ｜ {issue_meta['year']} 第 {issue_meta['week']} 週 ★最新刊</span>
        <h2>{title}</h2>
        <p class="desc">{desc}</p>
      </div>
      <div class="issue-footer">
        <span>📅 {date_str.replace('-', '/')} 出刊</span>
        <span class="action-btn-pill">進入 {code} 課程 →</span>
      </div>
    </a>"""

    # 移除舊卡片上的 ★最新刊 標記
    content = content.replace("★最新刊", "")

    # 插入到 #recent-grid
    recent_grid_marker = '<div class="archive-grid" id="recent-grid">\n'
    if recent_grid_marker in content:
        content = content.replace(recent_grid_marker, recent_grid_marker + new_recent_card + "\n\n", 1)

    # 4. 更新下期預告卡片
    upcoming_card = f"""    <!-- Upcoming Issue {next_info['code']} Card -->
    <div 
      class="issue-card" 
      style="opacity: 0.65; cursor: default;" 
      data-code="{next_info['code']}" 
      data-title="{next_info['title']}" 
      data-desc="{next_info['desc']}"
      data-tags="{next_info.get('tags', '')}"
    >
      <div>
        <span class="issue-badge" style="background: rgba(168, 85, 247, 0.15); color: #a78bfa; border-color: rgba(168, 85, 247, 0.3);">{next_info['code']} ｜ 預告</span>
        <h2>{next_info['title']}</h2>
        <p class="desc">{next_info['desc']}</p>
      </div>
      <div class="issue-footer">
        <span>📅 {next_info['date'].replace('-', '/')} 出刊</span>
        <span style="color:#a78bfa; font-size:13.5px;">即將推出 ⏳</span>
      </div>
    </div>"""

    content = re.sub(
        r'<!-- Upcoming Issue [^>]+ Card -->\s*<div class="issue-card" style="opacity: 0\.65;[\s\S]*?</div>\s*</div>',
        upcoming_card,
        content,
        count=1,
    )

    # 5. 在 #grid-2026 插入歷史歸檔卡片
    new_archive_card = f"""          <!-- {code} Archive Card -->
          <a 
            href="{code}.html" 
            class="issue-card" 
            data-code="{code}" 
            data-title="{title}" 
            data-desc="{desc}"
            data-tags="{data.get('search_tags', '')}"
          >
            <div>
              <span class="issue-badge">{code} ｜ {issue_meta['year']} 第 {issue_meta['week']} 週</span>
              <h2>{title}</h2>
              <p class="desc">{desc}</p>
            </div>
            <div class="issue-footer">
              <span>📅 {date_str.replace('-', '/')} 出刊</span>
              <span class="action-btn-pill">閱讀歸檔 →</span>
            </div>
          </a>"""

    grid_marker = '<div class="archive-grid" style="margin-bottom:0;" id="grid-2026">\n'
    if grid_marker in content:
        content = content.replace(grid_marker, grid_marker + new_archive_card + "\n\n", 1)

    # 6. 更新手風琴計數 (count-2026)
    count_match = re.search(r'id="count-2026">共 (\d+) 期</span>', content)
    if count_match:
        current_count = int(count_match.group(1))
        content = content.replace(
            f'id="count-2026">共 {current_count} 期</span>',
            f'id="count-2026">共 {current_count + 1} 期</span>',
            1,
        )

    INDEX_PATH.write_text(content, encoding="utf-8")
    print(f"[SUCCESS] 成功更新首頁門戶: {INDEX_PATH.name}")


def verify_pages_live(issue_code, max_retries=18, delay=10):
    """防呆檢查：輪詢確認 GitHub Pages 網址已完成部署（HTTP 200 OK，非 404）"""
    url = f"https://voyagermartin.github.io/Thai_Weekly/{issue_code}.html"
    print(f"\n[INFO] 開始驗證 GitHub Pages 上線狀態: {url}")
    
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.head(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200:
                print(f"[SUCCESS] 第 {attempt}/{max_retries} 次確認：網頁已順利上線 (HTTP 200 OK)！")
                return True
            else:
                print(f"[WAIT] 第 {attempt}/{max_retries} 次回傳 HTTP {resp.status_code}，等待 {delay} 秒後重試...")
        except requests.RequestException as e:
            print(f"[WAIT] 請求異常 ({e})，等待 {delay} 秒後重試...")
        
        time.sleep(delay)
    
    raise TimeoutError(f"GitHub Pages 在 {max_retries * delay} 秒內未完成部署 (非 200)！為避免讀者收到 404 連結，終止寄信流程。")


def send_individual_emails(issue_code, subject_override=None, recipient_filter=None):
    """讀取 email_{code}.html 並透過 Gmail SMTP 個別發送一對一專屬信件"""
    gmail_user = os.environ.get("GMAIL_USER", "voyager.martin@gmail.com")
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD")
    
    if not gmail_password:
        print("[ERROR] 未偵測到環境變數 GMAIL_APP_PASSWORD！無法發送 Email。")
        print("請在 GitHub 倉庫 Secrets 或本地環境設定 GMAIL_APP_PASSWORD。")
        sys.exit(1)

    email_file = ROOT_DIR / f"email_{issue_code}.html"
    if not email_file.exists():
        raise FileNotFoundError(f"找不到對應的電子報檔案: {email_file}")

    template_html = email_file.read_text(encoding="utf-8")

    # 決定主旨
    if subject_override:
        subject = subject_override
    else:
        # 從 email html 標題提取
        title_match = re.search(r'<h1 class="title">([^<]+)</h1>', template_html)
        title_text = title_match.group(1).strip() if title_match else f"VOL. {issue_code} 特輯"
        subject = f"【泰語學習週報】VOL. {issue_code} ｜ {title_text}"

    # 篩選收件人
    target_recipients = []
    for name, email, greeting in RECIPIENTS:
        if recipient_filter:
            if not any(f.lower() in email.lower() or f.lower() in name.lower() for f in recipient_filter):
                continue
        target_recipients.append((name, email, greeting))

    print(f"\n[INFO] 準備透過 Gmail SMTP ({gmail_user}) 發送 {len(target_recipients)} 封獨立電子郵件...")
    print(f"[INFO] 信件主旨: {subject}")

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(gmail_user, gmail_password)
        print("[INFO] Gmail SMTP 登入驗證成功！開始逐一寄送...")

        for name, email, greeting in target_recipients:
            # 替換專屬問候語
            personalized_html = template_html.replace("{{RECIPIENT_NAME}}", name)
            
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"Thai Weekly (泰語學習週報) <{gmail_user}>"
            msg["To"] = email
            msg.attach(MIMEText(personalized_html, "html", "utf-8"))

            server.sendmail(gmail_user, [email], msg.as_string())
            print(f"[SENT] 成功寄送專屬信件至: {name} <{email}> (問候語: {greeting})")
            time.sleep(1.5)  # 禮貌性間隔

    print("[SUCCESS] 所有專屬信件均已安全發送完畢！")


def main():
    parser = argparse.ArgumentParser(description="Thai_Weekly 全自動化發布與寄信系統")
    parser.add_argument(
        "--step",
        choices=["generate", "verify-and-send", "all", "resend"],
        default="all",
        help="執行階段: generate (生成網頁與首頁), verify-and-send (驗證網址並寄信), all (完整執行), resend (補寄特定期數)",
    )
    parser.add_argument("--issue", type=str, default=None, help="指定期數 (如 26w43、26w44)")
    parser.add_argument("--subject", type=str, default=None, help="自訂信件主旨")
    parser.add_argument("--recipients", type=str, default=None, help="以逗號分隔指定收件人 (如 annie,chang)")
    args = parser.parse_args()

    issue_meta = get_current_issue_meta(args.issue)
    api_key = os.environ.get("GEMINI_API_KEY")

    if args.step in ["generate", "all"]:
        if not api_key:
            print("[ERROR] 未設定環境變數 GEMINI_API_KEY！無法呼叫 Gemini API。")
            sys.exit(1)

        upcoming = extract_upcoming_from_index()
        print(f"[INFO] 取得預告卡片主題: {upcoming}")
        
        data = generate_lesson_content(issue_meta, upcoming, api_key)
        out_html = render_lesson_html(data, issue_meta)
        out_email = render_email_html(data, issue_meta)
        update_index_html(data, issue_meta)
        print(f"[DONE] 本週教學內容與首頁更新完畢: {data['issue_code']}")

    if args.step in ["verify-and-send", "all"]:
        code = args.issue or issue_meta["issue_code"]
        verify_pages_live(code)
        send_individual_emails(code, subject_override=args.subject)

    if args.step == "resend":
        code = args.issue or "26w43"
        recips = [r.strip() for r in args.recipients.split(",")] if args.recipients else None
        verify_pages_live(code, max_retries=3, delay=2)
        send_individual_emails(code, subject_override=args.subject, recipient_filter=recips)


if __name__ == "__main__":
    main()
