#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_to_sheet.py
呼叫 Web App 的 doPost(action="init_database") 初始化與寫入所有資料
"""

import sys
import json
from pathlib import Path
import requests

sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent.parent
from parse_lessons import parse_lesson_file
from deploy_gas import get_oauth_token

WEBAPP_URL = "https://script.google.com/macros/s/AKfycbz5ZuARMxkr12MZOYdB_3eKtKLURIU6KeivZf5-XRjLhk0zqQx2u-4LnlgXMGYIj6At/exec"


def main():
    token = get_oauth_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    issues_rows = []
    vocab_rows = []
    sentences_rows = []
    grammar_rows = []

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

    # 加入 26w44 預告
    issues_rows.append([
        "26w44", "2026", "44", "2026-10-31", "upcoming",
        "泰式按摩SPA・藥局問診與身體部位實務",
        "預計介紹泰式古法按摩力道調整、精油SPA預約與身體部位痠痛表達",
        "掌握藥局常備藥購買實用泰語，解析泰式草藥球與傳統醫學養生文化",
        "約 10 分鐘",
        "9個核心單字 ｜ 5組日常對話 ｜ 2大核心語法 ｜ 泰式草藥醫學文化誌",
        "", "", "", "", "", ""
    ])

    payload = {
        "action": "init_database",
        "data": {
            "issues": issues_rows,
            "vocab": vocab_rows,
            "sentences": sentences_rows,
            "grammar": grammar_rows,
        }
    }

    print(f"[INFO] 正在向 Web App 發送 init_database 請求 (包含 {len(issues_rows)} 期, {len(vocab_rows)} 個單字)...")
    r = requests.post(WEBAPP_URL, headers=headers, json=payload, allow_redirects=True, timeout=60)
    print("Web App 回應狀態碼:", r.status_code)
    print("Web App 回應內容:", r.text)

    # 設置觸發器
    print("[INFO] 正在設定每週六 09:00 排程觸發器...")
    r_trig = requests.post(WEBAPP_URL, headers=headers, json={"action": "setup_trigger"}, allow_redirects=True, timeout=30)
    print("設定觸發器回應:", r_trig.text)

if __name__ == "__main__":
    main()
