#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
upload_to_drive.py

將專案中的關鍵模板與手冊寫回 Google Drive 目標資料夾：
目標資料夾: 泰文小短篇 (Folder ID: 1xTWvfaAEIqzHFpDKtG7ipdMBZf8PYbBA)

預設同步檔案：
1. templates/lesson_template.html -> 供 Spark 參考與生成每週文章的標準骨架
2. HANDBOOK.MD -> 協作手冊與排版規範
"""

import os
import sys
import json
import mimetypes
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# ================= 設定區 =================
FOLDER_ID = "1xTWvfaAEIqzHFpDKtG7ipdMBZf8PYbBA"
SCOPES = ["https://www.googleapis.com/auth/drive"]
ROOT_DIR = Path(__file__).resolve().parent

# 欲上傳回 Google Drive 的本地檔案列表
TARGET_FILES = [
    ROOT_DIR / "templates" / "lesson_template.html",
    ROOT_DIR / "HANDBOOK.MD",
]


def get_credentials():
    """取得 Google Cloud 服務帳號憑證（優先從環境變數讀取 JSON 字串，次之讀取本地憑證檔）"""
    sa_json_env = os.environ.get("GCP_SA_KEY_JSON")
    if sa_json_env:
        print("[INFO] 從環境變數 GCP_SA_KEY_JSON 載入憑證...")
        try:
            info = json.loads(sa_json_env)
            return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        except json.JSONDecodeError as e:
            print(f"[ERROR] 解析 GCP_SA_KEY_JSON 失敗: {e}")
            sys.exit(1)

    sa_file_candidates = [
        os.environ.get("GCP_SA_KEY_PATH"),
        ROOT_DIR / "service_account.json",
        ROOT_DIR / "credentials.json",
    ]

    for candidate in sa_file_candidates:
        if candidate and Path(candidate).is_file():
            print(f"[INFO] 從本機檔案 {candidate} 載入憑證...")
            return service_account.Credentials.from_service_account_file(str(candidate), scopes=SCOPES)

    print("[ERROR] 未找到有效的 Google 服務帳號憑證！請設定 GCP_SA_KEY_JSON 環境變數或在本地提供 service_account.json。")
    sys.exit(1)


def find_drive_file(service, folder_id: str, filename: str):
    """檢查 Google Drive 資料夾內是否已存在同名檔案"""
    query = f"'{folder_id}' in parents and name = '{filename}' and trashed = false"
    response = service.files().list(
        q=query,
        spaces="drive",
        fields="files(id, name, mimeType, modifiedTime)",
        pageSize=10,
    ).execute()
    files = response.get("files", [])
    return files[0] if files else None


def upload_or_update_file(service, folder_id: str, file_path: Path):
    """上傳或更新單一檔案至 Google Drive"""
    if not file_path.exists():
        print(f"[WARN] 檔案不存在，略過: {file_path}")
        return

    filename = file_path.name
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if mime_type is None:
        if file_path.suffix.lower() == ".md":
            mime_type = "text/markdown"
        else:
            mime_type = "text/plain"

    media = MediaFileUpload(str(file_path), mimetype=mime_type, resumable=True)

    existing_file = find_drive_file(service, folder_id, filename)

    if existing_file:
        file_id = existing_file["id"]
        print(f"[INFO] 更新雲端既有檔案: {filename} (ID: {file_id})...")
        updated_file = service.files().update(
            fileId=file_id,
            media_body=media,
            fields="id, name, modifiedTime"
        ).execute()
        print(f"[SUCCESS] 已更新: {filename} -> {updated_file.get('modifiedTime')}")
    else:
        print(f"[INFO] 雲端無同名檔案，建立新檔案: {filename}...")
        file_metadata = {
            "name": filename,
            "parents": [folder_id],
        }
        new_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, name"
        ).execute()
        print(f"[SUCCESS] 已建立: {filename} (ID: {new_file.get('id')})")


def main():
    print("=" * 60)
    print("Thai_Weekly 本地檔案寫回 Google Drive 工具")
    print(f"目標雲端資料夾 ID: {FOLDER_ID}")
    print("=" * 60)

    creds = get_credentials()
    service = build("drive", "v3", credentials=creds)

    for target in TARGET_FILES:
        upload_or_update_file(service, FOLDER_ID, target)

    print("\n[FINISH] 所有指定檔案已同步至 Google Drive！")


if __name__ == "__main__":
    main()
