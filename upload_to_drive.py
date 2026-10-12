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
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()
    files = response.get("files", [])
    return files[0] if files else None


def upload_or_update_file(service, folder_id: str, file_path: Path, sa_email: str):
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

    print(f"\n[START] 處理檔案: {filename} ({mime_type})")
    media = MediaFileUpload(str(file_path), mimetype=mime_type, resumable=True)

    try:
        existing_file = find_drive_file(service, folder_id, filename)

        if existing_file:
            file_id = existing_file["id"]
            print(f"[INFO] 雲端已存在同名檔案，執行更新: {filename} (ID: {file_id})...")
            updated_file = service.files().update(
                fileId=file_id,
                media_body=media,
                fields="id, name, modifiedTime",
                supportsAllDrives=True,
            ).execute()
            print(f"[SUCCESS] 已成功更新檔案: {filename} (時間: {updated_file.get('modifiedTime')})")
        else:
            print(f"[INFO] 雲端尚無同名檔案，建立新檔案: {filename}...")
            file_metadata = {
                "name": filename,
                "parents": [folder_id],
            }
            new_file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id, name",
                supportsAllDrives=True,
            ).execute()
            print(f"[SUCCESS] 已成功建立檔案: {filename} (ID: {new_file.get('id')})")

    except HttpError as e:
        status_code = e.resp.status if hasattr(e, "resp") else "未知"
        error_details = e.content.decode("utf-8", errors="ignore") if hasattr(e, "content") else str(e)
        print("\n" + "=" * 65)
        print(f"[ERROR] 上傳檔案「{filename}」時發生 Google Drive API 錯誤 (HTTP {status_code})")
        print(f"詳細錯誤訊息: {error_details}")
        print("-" * 65)
        if status_code in (403, 404):
            print("【權限排除指引】")
            print(f"1. 請開啟 Google Drive 目標資料夾「泰文小短篇」(ID: {folder_id})")
            print(f"2. 點選「共用」設定，確認是否已將此服務帳號加入：")
            print(f"   👉 {sa_email}")
            print(f"3. 請務必將該帳號權限設為「編輯者 (Editor)」（不可為檢視者）！")
        print("=" * 65 + "\n")
        raise e


def main():
    print("=" * 65)
    print("Thai_Weekly 本地檔案寫回 Google Drive 工具")
    print(f"目標雲端資料夾 ID: {FOLDER_ID}")
    print("=" * 65)

    creds = get_credentials()
    sa_email = getattr(creds, "service_account_email", "未知帳號")
    print(f"[INFO] 驗證成功！目前使用的 GCP 服務帳號: {sa_email}")

    service = build("drive", "v3", credentials=creds)

    has_error = False
    for target in TARGET_FILES:
        try:
            upload_or_update_file(service, FOLDER_ID, target, sa_email)
        except Exception:
            has_error = True

    if has_error:
        print("\n[FAILED] 部分或全部檔案上傳失敗，請依上方指引檢查 Google Drive 編輯權限。")
        sys.exit(1)

    print("\n[FINISH] ✨ 所有指定檔案均已成功寫入 Google Drive 目標資料夾！")


if __name__ == "__main__":
    main()
