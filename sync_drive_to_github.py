#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_drive_to_github.py

Thai_Weekly 自動化同步管線：
1. 透過 Google Drive API 連線至目標資料夾「泰文小短篇」 (Folder ID: 1xTWvfaAEIqzHFpDKtG7ipdMBZf8PYbBA)。
2. 自動抓取資料夾內所有最新 .html 檔案（比對本地與雲端 MD5/檔案狀態，若有新增或更新則下載）。
3. 比對 Git 狀態，若有變更自動執行 git add、git commit 與 git push origin main。
"""

import os
import sys
import io
import json
import hashlib
import subprocess
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

# ================= 設定區 =================
FOLDER_ID = "1xTWvfaAEIqzHFpDKtG7ipdMBZf8PYbBA"
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
ROOT_DIR = Path(__file__).resolve().parent


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

    print("[ERROR] 未找到有效的 Google 服務帳號憑證！請設定 GCP_SA_KEY_JSON 環境變數或提供 service_account.json。")
    sys.exit(1)


def compute_file_md5(file_path: Path) -> str:
    """計算本機檔案的 MD5 雜湊值"""
    if not file_path.exists():
        return ""
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


def fetch_drive_html_files(service, folder_id: str):
    """取得 Google Drive 目標資料夾內的所有 .html 檔案清單"""
    query = f"'{folder_id}' in parents and trashed = false"
    print(f"[INFO] 查詢 Google Drive 資料夾 (ID: {folder_id})...")

    files = []
    page_token = None

    while True:
        response = service.files().list(
            q=query,
            spaces="drive",
            fields="nextPageToken, files(id, name, mimeType, md5Checksum, modifiedTime, size)",
            pageToken=page_token,
            pageSize=100,
        ).execute()

        for item in response.get("files", []):
            name = item.get("name", "")
            # 僅過濾 .html 檔案
            if name.lower().endswith(".html"):
                files.append(item)

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    print(f"[INFO] 雲端找到 {len(files)} 個 .html 檔案。")
    return files


def download_file(service, file_id: str, dest_path: Path):
    """下載 Google Drive 檔案至本機目標路徑"""
    request = service.files().get_media(fileId=file_id)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    with open(dest_path, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"  下載進度: {int(status.progress() * 100)}%")


def sync_html_files(service):
    """同步雲端 .html 檔案至專案目錄，並返回有更新的檔案清單"""
    remote_files = fetch_drive_html_files(service, FOLDER_ID)
    updated_files = []

    for file_info in remote_files:
        name = file_info["name"]
        file_id = file_info["id"]
        remote_md5 = file_info.get("md5Checksum")
        local_path = ROOT_DIR / name

        should_download = False
        if not local_path.exists():
            print(f"[NEW] 本機尚無此檔案: {name}，準備下載...")
            should_download = True
        else:
            local_md5 = compute_file_md5(local_path)
            if remote_md5 and local_md5 != remote_md5:
                print(f"[UPDATE] 檔案內容已變更 (MD5 不一致): {name}，準備重新下載...")
                should_download = True
            elif not remote_md5:
                # 若 Google Drive 未回傳 md5Checksum（例如 Google Docs 匯出等情況），直接下載比對
                print(f"[CHECK] 無法取得遠端 MD5，強制下載更新: {name}...")
                should_download = True
            else:
                print(f"[SKIP] 檔案已是最新版本: {name}")

        if should_download:
            try:
                download_file(service, file_id, local_path)
                print(f"[SUCCESS] 成功下載/更新: {name}")
                updated_files.append(name)
            except Exception as e:
                print(f"[ERROR] 下載檔案失敗 ({name}): {e}")

    return updated_files


def run_git_command(args, check=True):
    """執行 Git 命令並返回輸出結果"""
    cmd_str = " ".join(args)
    result = subprocess.run(args, cwd=ROOT_DIR, capture_output=True, text=True, check=False)
    if check and result.returncode != 0:
        print(f"[ERROR] 執行 Git 指令失敗: {cmd_str}\n{result.stderr}")
        raise RuntimeError(f"Git command failed: {cmd_str}")
    return result


def git_commit_and_push(updated_files):
    """自動執行 git add, git commit, git push origin main"""
    status_res = run_git_command(["git", "status", "--porcelain"], check=False)
    if not status_res.stdout.strip():
        print("[INFO] Working tree乾淨，無任何 Git 變更需要提交。")
        return

    print("[INFO] 偵測到本機檔案變更，準備提交至 GitHub...")

    # 在 CI 環境中若未設定 user.name / user.email，設定預設 bot 資訊
    config_name = run_git_command(["git", "config", "user.name"], check=False).stdout.strip()
    if not config_name:
        run_git_command(["git", "config", "user.name", "github-actions[bot]"])
        run_git_command(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"])

    # 執行 git add
    run_git_command(["git", "add", "."])

    # 產生 commit 訊息
    if updated_files:
        commit_msg = f"Auto-sync: 更新 {len(updated_files)} 個泰文週報檔案 ({', '.join(updated_files[:3])}{'...' if len(updated_files) > 3 else ''}) [skip ci]"
    else:
        commit_msg = "Auto-sync: 更新泰語學習週報最新內容 [skip ci]"

    print(f"[INFO] 提交變更: {commit_msg}")
    run_git_command(["git", "commit", "-m", commit_msg])

    # 執行 git push
    print("[INFO] 推送變更至 origin main...")
    push_res = run_git_command(["git", "push", "origin", "main"], check=False)
    if push_res.returncode == 0:
        print("[SUCCESS] 成功推送至 GitHub 倉庫 (origin/main)！")
    else:
        print(f"[WARNING] 推送失敗或非預設遠端分支:\n{push_res.stderr}")


def main():
    print("=" * 60)
    print("Thai_Weekly Google Drive -> GitHub 自動同步程序啟動")
    print("=" * 60)

    try:
        credentials = get_credentials()
        service = build("drive", "v3", credentials=credentials, cache_discovery=False)
        updated_files = sync_html_files(service)

        print("\n" + "=" * 60)
        print(f"檔案同步完成！共更新 {len(updated_files)} 個檔案。")
        print("=" * 60)

        git_commit_and_push(updated_files)
        print("\n[FINISH] 自動同步管線全部執行完畢。")

    except HttpError as error:
        print(f"[FATAL] Google Drive API 請求錯誤: {error}")
        sys.exit(1)
    except Exception as e:
        print(f"[FATAL] 發生未預期錯誤: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
