#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
deploy_gas.py
將 Google Apps Script 程式碼部署至 Thai_Weekly_Automation (綁定於 Thai_Weekly_DB 試算表)
"""

import sys
import json
from pathlib import Path
import requests

sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent.parent
SCRIPT_ID = "1fJ_JIB0aET_pLwDOJasv47YzSBn3xk7NhW3h96919NRd2opJpq-VOOmA"
SPREADSHEET_ID = "1DvxPjzNRlTRSMSXr6eaktU2dBQZSS9oWadNfT3_ZUTM"


def get_oauth_token():
    clasprc_path = Path(r"C:\Users\voyag\.clasprc.json")
    with open(clasprc_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    token_data = data["tokens"]["default"]
    resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": token_data["client_id"],
            "client_secret": token_data["client_secret"],
            "refresh_token": token_data["refresh_token"],
            "grant_type": "refresh_token",
        },
        timeout=15,
    )
    return resp.json()["access_token"]


def deploy_script_content(code_gs_content: str):
    token = get_oauth_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    manifest = {
        "timeZone": "Asia/Taipei",
        "dependencies": {},
        "exceptionLogging": "STACKDRIVER",
        "runtimeVersion": "V8",
        "oauthScopes": [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/script.external_request",
            "https://www.googleapis.com/auth/script.send_mail",
            "https://www.googleapis.com/auth/script.scriptapp",
        ],
    }

    payload = {
        "files": [
            {
                "name": "appsscript",
                "type": "JSON",
                "source": json.dumps(manifest, indent=2),
            },
            {
                "name": "Code",
                "type": "SERVER_JS",
                "source": code_gs_content,
            },
        ]
    }

    url = f"https://script.googleapis.com/v1/projects/{SCRIPT_ID}/content"
    resp = requests.put(url, headers=headers, json=payload, timeout=20)
    print("上傳 Apps Script 狀態碼:", resp.status_code)
    if resp.status_code == 200:
        print("[SUCCESS] Google Apps Script 程式碼已成功推送至雲端！")
    else:
        print("[ERROR]", resp.text)


def deploy_code_gs():
    code_path = ROOT_DIR / "gas" / "Code.gs"
    if not code_path.exists():
        raise FileNotFoundError(f"找不到 {code_path}")
    
    code_content = code_path.read_text(encoding="utf-8")
    token = get_oauth_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    manifest = {
        "timeZone": "Asia/Taipei",
        "dependencies": {},
        "exceptionLogging": "STACKDRIVER",
        "runtimeVersion": "V8",
        "webapp": {
            "access": "ANYONE",
            "executeAs": "USER_DEPLOYING"
        }
    }

    payload = {
        "files": [
            {
                "name": "appsscript",
                "type": "JSON",
                "source": json.dumps(manifest, indent=2),
            },
            {
                "name": "Code",
                "type": "SERVER_JS",
                "source": code_content,
            },
        ]
    }

    url = f"https://script.googleapis.com/v1/projects/{SCRIPT_ID}/content"
    resp = requests.put(url, headers=headers, json=payload, timeout=20)
    print("上傳 Apps Script 狀態碼:", resp.status_code)
    if resp.status_code != 200:
        print("[ERROR]", resp.text)
        return

    # 建立新版本
    r_ver = requests.post(f"https://script.googleapis.com/v1/projects/{SCRIPT_ID}/versions", headers=headers, json={"description": f"Code.gs update"})
    ver_num = r_ver.json()["versionNumber"]
    print(f"[SUCCESS] 建立版本: v{ver_num}")

    # 讀取現有 deployment_id
    config_path = ROOT_DIR / "scripts" / "db_config.json"
    dep_id = None
    cfg = {}
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            dep_id = cfg.get("DEPLOYMENT_ID")

    if dep_id:
        dep_url = f"https://script.googleapis.com/v1/projects/{SCRIPT_ID}/deployments/{dep_id}"
        dep_body = {
            "deploymentConfig": {
                "versionNumber": ver_num,
                "manifestFileName": "appsscript",
                "description": f"v{ver_num} deployment"
            }
        }
        r_dep = requests.put(dep_url, headers=headers, json=dep_body)
        print(f"[SUCCESS] 更新 Web App 部署狀態 ({dep_id}): {r_dep.status_code}")
    else:
        r_dep = requests.post(
            f"https://script.googleapis.com/v1/projects/{SCRIPT_ID}/deployments",
            headers=headers,
            json={
                "versionNumber": ver_num,
                "manifestFileName": "appsscript",
                "description": f"v{ver_num} deployment"
            }
        )
        print(f"[SUCCESS] 建立新 Web App 部署狀態: {r_dep.status_code}")
        dep_data = r_dep.json()
        dep_id = dep_data.get("deploymentId")

    exec_url = f"https://script.google.com/macros/s/{dep_id}/exec"
    print(f"Deployment ID: {dep_id}")
    print(f"Web App URL: {exec_url}")

    if config_path.exists():
        cfg["DEPLOYMENT_ID"] = dep_id
        cfg["WEBAPP_URL"] = exec_url
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        print("[SUCCESS] db_config.json 已同步更新！")

if __name__ == "__main__":
    deploy_code_gs()
