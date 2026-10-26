#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
setup_google_sheet.py
建立並初始化 Thai_Weekly_DB（泰語學習週報資料庫）Google Sheet：
- 目標資料夾: 泰文小短篇 (ID: 1xTWvfaAEIqzHFpDKtG7ipdMBZf8PYbBA)
- 建立 4 個分頁: Issues, Vocab, Sentences, Grammar
- 權限公開為「知道連結的任何人均可檢視」
- 匯入 26w41, 26w42, 26w43 以及 26w44 預告資料
"""

import sys
import json
import time
from pathlib import Path
import requests

sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent.parent
from parse_lessons import parse_lesson_file

FOLDER_ID = "1xTWvfaAEIqzHFpDKtG7ipdMBZf8PYbBA"
DB_NAME = "Thai_Weekly_DB（泰語學習週報資料庫）"


def get_oauth_token():
    clasprc_path = Path(r"C:\Users\voyag\.clasprc.json")
    if not clasprc_path.exists():
        raise FileNotFoundError(f"找不到 clasp 憑證檔: {clasprc_path}")
    
    with open(clasprc_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    token_data = data.get("tokens", {}).get("default", {})
    client_id = token_data.get("client_id")
    client_secret = token_data.get("client_secret")
    refresh_token = token_data.get("refresh_token")
    
    if not (client_id and client_secret and refresh_token):
        raise ValueError("clasprc 憑證不完整，缺少 client_id 或 refresh_token")

    resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=15,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"刷新 OAuth2 Token 失敗: {resp.status_code} {resp.text}")
    
    return resp.json()["access_token"]


def find_or_create_spreadsheet(token):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # 檢查是否已存在
    q = f"'{FOLDER_ID}' in parents and name = '{DB_NAME}' and trashed = false"
    url = f"https://www.googleapis.com/drive/v3/files?q={requests.utils.quote(q)}&fields=files(id,name)"
    r = requests.get(url, headers=headers, timeout=15)
    files = r.json().get("files", [])
    
    if files:
        sheet_id = files[0]["id"]
        print(f"[INFO] 找到已存在的試算表: {DB_NAME} (ID: {sheet_id})")
        return sheet_id, False
    
    # 建立新試算表
    print(f"[INFO] 建立新 Google Sheet: {DB_NAME} 於資料夾 {FOLDER_ID}...")
    create_url = "https://www.googleapis.com/drive/v3/files"
    meta = {
        "name": DB_NAME,
        "mimeType": "application/vnd.google-apps.spreadsheet",
        "parents": [FOLDER_ID],
    }
    r_create = requests.post(create_url, json=meta, headers=headers, timeout=20)
    if r_create.status_code != 200:
        raise RuntimeError(f"建立試算表失敗: {r_create.status_code} {r_create.text}")
    
    sheet_id = r_create.json()["id"]
    print(f"[SUCCESS] 試算表建立成功！ID: {sheet_id}")
    return sheet_id, True


def set_public_permission(token, sheet_id):
    """將權限設為知道連結的任何人均可檢視 (role=reader, type=anyone)"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = f"https://www.googleapis.com/drive/v3/files/{sheet_id}/permissions"
    perm = {"role": "reader", "type": "anyone"}
    r = requests.post(url, json=perm, headers=headers, timeout=15)
    if r.status_code in [200, 201]:
        print("[SUCCESS] 權限已設為「知道連結的任何人均可檢視」")
    else:
        print(f"[WARN] 設定共用權限回傳: {r.status_code} {r.text}")


def init_tabs_and_headers(token, sheet_id):
    """初始化 4 個工作表 Tabs: Issues, Vocab, Sentences, Grammar"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # 取得現有 sheets
    r = requests.get(f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}", headers=headers, timeout=15)
    sheet_meta = r.json()
    existing_sheets = {s["properties"]["title"]: s["properties"]["sheetId"] for s in sheet_meta.get("sheets", [])}
    
    target_tabs = ["Issues", "Vocab", "Sentences", "Grammar"]
    requests_body = []
    
    # 建立不存在的 tab
    for tab in target_tabs:
        if tab not in existing_sheets:
            requests_body.append({
                "addSheet": {
                    "properties": {
                        "title": tab,
                        "gridProperties": {"rowCount": 100, "columnCount": 20}
                    }
                }
            })
            
    if requests_body:
        r_add = requests.post(
            f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}:batchUpdate",
            json={"requests": requests_body},
            headers=headers,
            timeout=15
        )
        print("[INFO] 建立分頁結果:", r_add.status_code)
        
    # 刪除預設的 Sheet1 / 工作表1 (若 target_tabs 已建立)
    r_refresh = requests.get(f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}", headers=headers, timeout=15)
    current_sheets = r_refresh.json().get("sheets", [])
    delete_reqs = []
    for s in current_sheets:
        title = s["properties"]["title"]
        if title not in target_tabs and len(current_sheets) - len(delete_reqs) > 1:
            delete_reqs.append({"deleteSheet": {"sheetId": s["properties"]["sheetId"]}})
            
    if delete_reqs:
        requests.post(
            f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}:batchUpdate",
            json={"requests": delete_reqs},
            headers=headers,
            timeout=15
        )
        print("[INFO] 移除預設多餘分頁。")

    # 設定各分頁的標題列 (Header Row)
    header_data = [
        {
            "range": "Issues!A1:P1",
            "values": [[
                "issue_code", "year", "week", "publish_date", "status", "title",
                "subtitle_1", "subtitle_2", "read_time", "highlights",
                "culture_title", "culture_body_html", "culture_memo_html",
                "email_subject", "email_intro_html", "email_highlights_html"
            ]]
        },
        {
            "range": "Vocab!A1:E1",
            "values": [["issue_code", "type", "thai", "phonetic", "meaning"]]
        },
        {
            "range": "Sentences!A1:E1",
            "values": [["issue_code", "order", "thai", "phonetic", "meaning"]]
        },
        {
            "range": "Grammar!A1:E1",
            "values": [["issue_code", "point_num", "title", "explanation_html", "examples_json"]]
        }
    ]
    
    r_head = requests.post(
        f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values:batchUpdate",
        json={"valueInputOption": "USER_ENTERED", "data": header_data},
        headers=headers,
        timeout=15
    )
    print(f"[SUCCESS] 各分頁標題列配置完成: {r_head.status_code}")


def populate_initial_data(token, sheet_id):
    """解析並填入 26w41, 26w42, 26w43 以及 26w44 預告資料"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    issues_rows = []
    vocab_rows = []
    sentences_rows = []
    grammar_rows = []
    
    # 依序解析 26w41, 26w42, 26w43
    for file_name in ["26w41.html", "26w42.html", "26w43.html"]:
        p = ROOT_DIR / file_name
        if not p.exists():
            continue
        parsed = parse_lesson_file(p)
        iss = parsed["issue"]
        issues_rows.append([
            iss["issue_code"], iss["year"], iss["week"], iss["publish_date"], iss["status"],
            iss["title"], iss["subtitle_1"], iss["subtitle_2"], iss["read_time"], iss["highlights"],
            iss["culture_title"], iss["culture_body_html"], iss["culture_memo_html"],
            iss["email_subject"], iss["email_intro_html"], iss["email_highlights_html"]
        ])
        
        for v in parsed["vocab"]:
            vocab_rows.append([v["issue_code"], v["type"], v["thai"], v["phonetic"], v["meaning"]])
            
        for s in parsed["sentences"]:
            sentences_rows.append([s["issue_code"], s["order"], s["thai"], s["phonetic"], s["meaning"]])
            
        for g in parsed["grammar"]:
            grammar_rows.append([g["issue_code"], g["point_num"], g["title"], g["explanation_html"], g["examples_json"]])

    # 加入 26w44 預告列 (status = upcoming)
    issues_rows.append([
        "26w44", "2026", "44", "2026-10-31", "upcoming",
        "泰式按摩SPA・藥局問診與身體部位實務",
        "預計介紹泰式古法按摩力道調整、精油SPA預約與身體部位痠痛表達",
        "掌握藥局常備藥購買實用泰語，解析泰式草藥球與傳統醫學養生文化",
        "約 10 分鐘",
        "9個核心單字 ｜ 5組日常對話 ｜ 2大核心語法 ｜ 泰式草藥醫學文化誌",
        "", "", "", "", "", ""
    ])

    # 批次清除並填入數據 (從 A2 開始)
    # 先清除 A2:Z
    for tab in ["Issues", "Vocab", "Sentences", "Grammar"]:
        requests.post(
            f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{tab}!A2:Z:clear",
            headers=headers,
            timeout=15
        )
        
    batch_values = [
        {"range": f"Issues!A2:P{len(issues_rows)+1}", "values": issues_rows},
        {"range": f"Vocab!A2:E{len(vocab_rows)+1}", "values": vocab_rows},
        {"range": f"Sentences!A2:E{len(sentences_rows)+1}", "values": sentences_rows},
        {"range": f"Grammar!A2:E{len(grammar_rows)+1}", "values": grammar_rows},
    ]
    
    r_pop = requests.post(
        f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values:batchUpdate",
        json={"valueInputOption": "USER_ENTERED", "data": batch_values},
        headers=headers,
        timeout=25
    )
    print(f"[SUCCESS] 歷史期數數據匯入成功！狀態碼: {r_pop.status_code}")
    print(f"  • Issues 列數: {len(issues_rows)}")
    print(f"  • Vocab 列數: {len(vocab_rows)}")
    print(f"  • Sentences 列數: {len(sentences_rows)}")
    print(f"  • Grammar 列數: {len(grammar_rows)}")


def main():
    print("=== 開始建立與初始化 Thai_Weekly_DB Google Sheet ===")
    token = get_oauth_token()
    sheet_id, is_new = find_or_create_spreadsheet(token)
    set_public_permission(token, sheet_id)
    init_tabs_and_headers(token, sheet_id)
    populate_initial_data(token, sheet_id)
    
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
    print("\n🎉 Google Sheet 資料庫就緒！")
    print(f"Spreadsheet ID: {sheet_id}")
    print(f"Spreadsheet URL: {sheet_url}")
    print(f"GViz JSON Endpoint: https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:json&sheet=Issues")
    
    # 儲存 config 至本地供前端或腳本讀取
    config = {
        "SPREADSHEET_ID": sheet_id,
        "SPREADSHEET_URL": sheet_url,
        "FOLDER_ID": FOLDER_ID,
        "TABS": ["Issues", "Vocab", "Sentences", "Grammar"],
    }
    (ROOT_DIR / "scripts" / "db_config.json").write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    print("已將設定寫入 scripts/db_config.json")

if __name__ == "__main__":
    main()
