#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
create_sheet_from_xlsx.py
建立包含 4 個工作表的 Excel 檔案，並透過 Google Drive API multipart 上傳轉換為原生 Google Sheet。
"""

import sys
import json
import io
from pathlib import Path
import openpyxl
import requests

sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent.parent
from parse_lessons import parse_lesson_file
from deploy_gas import get_oauth_token

FOLDER_ID = "1xTWvfaAEIqzHFpDKtG7ipdMBZf8PYbBA"
DB_NAME = "Thai_Weekly_DB（泰語學習週報資料庫）"


def build_workbook():
    wb = openpyxl.Workbook()
    # 預設 sheet 改為 Issues
    ws_issues = wb.active
    ws_issues.title = "Issues"
    ws_vocab = wb.create_sheet(title="Vocab")
    ws_sentences = wb.create_sheet(title="Sentences")
    ws_grammar = wb.create_sheet(title="Grammar")

    # Headers
    ws_issues.append([
        "issue_code", "year", "week", "publish_date", "status", "title",
        "subtitle_1", "subtitle_2", "read_time", "highlights",
        "culture_title", "culture_body_html", "culture_memo_html",
        "email_subject", "email_intro_html", "email_highlights_html"
    ])
    ws_vocab.append(["issue_code", "type", "thai", "phonetic", "meaning"])
    ws_sentences.append(["issue_code", "order", "thai", "phonetic", "meaning"])
    ws_grammar.append(["issue_code", "point_num", "title", "explanation_html", "examples_json"])

    # 匯入 26w41, 26w42, 26w43
    for fn in ["26w41.html", "26w42.html", "26w43.html"]:
        p = ROOT_DIR / fn
        if not p.exists():
            continue
        parsed = parse_lesson_file(p)
        iss = parsed["issue"]
        ws_issues.append([
            iss["issue_code"], iss["year"], iss["week"], iss["publish_date"], iss["status"],
            iss["title"], iss["subtitle_1"], iss["subtitle_2"], iss["read_time"], iss["highlights"],
            iss["culture_title"], iss["culture_body_html"], iss["culture_memo_html"],
            iss["email_subject"], iss["email_intro_html"], iss["email_highlights_html"]
        ])
        for v in parsed["vocab"]:
            ws_vocab.append([v["issue_code"], v["type"], v["thai"], v["phonetic"], v["meaning"]])
        for s in parsed["sentences"]:
            ws_sentences.append([s["issue_code"], s["order"], s["thai"], s["phonetic"], s["meaning"]])
        for g in parsed["grammar"]:
            ws_grammar.append([g["issue_code"], g["point_num"], g["title"], g["explanation_html"], g["examples_json"]])

    # 匯入 26w44 預告
    ws_issues.append([
        "26w44", "2026", "44", "2026-10-31", "upcoming",
        "泰式按摩SPA・藥局問診與身體部位實務",
        "預計介紹泰式古法按摩力道調整、精油SPA預約與身體部位痠痛表達",
        "掌握藥局常備藥購買實用泰語，解析泰式草藥球與傳統醫學養生文化",
        "約 10 分鐘",
        "9個核心單字 ｜ 5組日常對話 ｜ 2大核心語法 ｜ 泰式草藥醫學文化誌",
        "", "", "", "", "", ""
    ])

    xlsx_path = ROOT_DIR / "scripts" / "Thai_Weekly_DB.xlsx"
    wb.save(xlsx_path)
    print(f"[SUCCESS] 本地已生成完整資料庫 Excel 檔: {xlsx_path}")
    return xlsx_path


def upload_and_convert_to_google_sheet(xlsx_path: Path):
    token = get_oauth_token()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. 檢查既有的舊檔案，若有則先移至垃圾桶或更新
    q = f"'{FOLDER_ID}' in parents and name = '{DB_NAME}' and trashed = false"
    url_list = f"https://www.googleapis.com/drive/v3/files?q={requests.utils.quote(q)}"
    r_list = requests.get(url_list, headers=headers).json()
    for f in r_list.get("files", []):
        old_id = f["id"]
        print(f"[INFO] 刪除既有同名檔案: {old_id}")
        requests.delete(f"https://www.googleapis.com/drive/v3/files/{old_id}", headers=headers)

    # 2. Multipart 上傳並自動轉換為 Google Sheet
    metadata = {
        "name": DB_NAME,
        "mimeType": "application/vnd.google-apps.spreadsheet",
        "parents": [FOLDER_ID]
    }
    
    files = {
        "data": ("metadata", json.dumps(metadata), "application/json; charset=UTF-8"),
        "file": (xlsx_path.name, open(xlsx_path, "rb"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    }

    print(f"[INFO] 正在上傳並轉換為 Google Sheet: {DB_NAME}...")
    upload_url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
    r_up = requests.post(upload_url, headers=headers, files=files, timeout=40)
    print("上傳轉換狀態碼:", r_up.status_code)
    
    if r_up.status_code not in [200, 201]:
        raise RuntimeError(f"上傳轉換失敗: {r_up.text}")
        
    sheet_data = r_up.json()
    sheet_id = sheet_data["id"]
    print(f"[SUCCESS] 試算表轉換建立成功！ID: {sheet_id}")

    # 3. 設定公開權限 (anyone with link can view)
    perm_url = f"https://www.googleapis.com/drive/v3/files/{sheet_id}/permissions"
    r_perm = requests.post(perm_url, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json={"role": "reader", "type": "anyone"}, timeout=15)
    print(f"[SUCCESS] 設定共用檢視權限狀態: {r_perm.status_code}")

    # 4. 儲存至 db_config.json
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
    cfg = {
        "SPREADSHEET_ID": sheet_id,
        "SPREADSHEET_URL": sheet_url,
        "FOLDER_ID": FOLDER_ID,
        "TABS": ["Issues", "Vocab", "Sentences", "Grammar"]
    }
    (ROOT_DIR / "scripts" / "db_config.json").write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n🎉 試算表資料庫配置完成！\n網址: {sheet_url}")
    return sheet_id


if __name__ == "__main__":
    xlsx_file = build_workbook()
    new_sheet_id = upload_and_convert_to_google_sheet(xlsx_file)
