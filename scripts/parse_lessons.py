#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parse_lessons.py
從本地 26w41.html, 26w42.html, 26w43.html 解析出結構化數據，供寫入 Google Sheet。
"""

import sys
import re
import json
from pathlib import Path
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent.parent

def parse_lesson_file(file_path: Path):
    content = file_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(content, "html.parser")
    
    # 提取期數中繼
    mag_header = soup.select_one(".mag-header")
    vol_tag = mag_header.select_one(".mag-tag-vol").get_text(strip=True) if mag_header else ""
    
    # 匹配 issue_code, year, week
    m = re.search(r"VOL\.\s*(\d{2}w\d{2})", vol_tag)
    issue_code = m.group(1) if m else file_path.stem
    
    m_yw = re.search(r"(\d{4})\s*第\s*(\d+)\s*週", vol_tag)
    year = m_yw.group(1) if m_yw else "2026"
    week = m_yw.group(2) if m_yw else issue_code.split("w")[-1]
    
    # 提取日期
    date_span = ""
    for s in mag_header.select(".mag-meta-row span"):
        text = s.get_text(strip=True)
        if re.search(r"\d{4}-\d{2}-\d{2}", text):
            date_span = re.search(r"\d{4}-\d{2}-\d{2}", text).group(0)
            break
    if not date_span:
        # 預設對應
        date_map = {"26w41": "2026-10-10", "26w42": "2026-10-17", "26w43": "2026-10-24"}
        date_span = date_map.get(issue_code, "2026-10-24")

    title = mag_header.select_one(".mag-title").get_text(strip=True) if mag_header.select_one(".mag-title") else ""
    
    # subtitle
    sub_spans = mag_header.select(".mag-subtitle span")
    subtitle_1 = sub_spans[0].get_text(strip=True) if len(sub_spans) > 0 else ""
    subtitle_2 = sub_spans[1].get_text(strip=True) if len(sub_spans) > 1 else ""
    if not subtitle_1 and mag_header.select_one(".mag-subtitle"):
        subtitle_1 = mag_header.select_one(".mag-subtitle").get_text(strip=True)
    
    # footer pills
    read_time = "10 分鐘"
    highlights = ""
    for pill in mag_header.select(".mag-pill"):
        txt = pill.get_text(strip=True)
        if "閱讀時間" in txt:
            read_time = txt.split("：")[-1].strip()
        elif "本期重點" in txt:
            highlights = txt.split("：")[-1].strip()

    # 1. Vocab (Core)
    vocab_list = []
    for card in soup.select(".vocab-card"):
        thai = card.select_one(".thai-word").get_text(strip=True) if card.select_one(".thai-word") else ""
        phonetic = card.select_one(".phonetic").get_text(strip=True) if card.select_one(".phonetic") else ""
        meaning = card.select_one(".meaning").get_text(strip=True) if card.select_one(".meaning") else ""
        if thai:
            vocab_list.append({
                "issue_code": issue_code,
                "type": "core",
                "thai": thai,
                "phonetic": phonetic,
                "meaning": meaning
            })

    # 2. Sentences
    sentences_list = []
    for idx, card in enumerate(soup.select(".sentence-card"), start=1):
        thai = card.select_one(".sentence-thai").get_text(strip=True) if card.select_one(".sentence-thai") else ""
        phonetic = card.select_one(".sentence-phonetic").get_text(strip=True) if card.select_one(".sentence-phonetic") else ""
        meaning = card.select_one(".sentence-meaning").get_text(strip=True) if card.select_one(".sentence-meaning") else ""
        if thai:
            sentences_list.append({
                "issue_code": issue_code,
                "order": idx,
                "thai": thai,
                "phonetic": phonetic,
                "meaning": meaning
            })

    # 3. Grammar
    grammar_list = []
    for idx, card in enumerate(soup.select(".grammar-card"), start=1):
        title_el = card.select_one(".grammar-card-title")
        g_title = title_el.get_text(strip=True) if title_el else f"語法重點 {idx}"
        # 移除前綴
        g_title = re.sub(r"^💡\s*語法重點\s*\d+[:：]\s*", "", g_title)
        
        # explanation
        exp_p = card.select_one("p")
        exp_html = "".join([str(c) for c in exp_p.contents]).strip() if exp_p else ""
        
        # examples
        examples = []
        for pill in card.select(".example-pill"):
            th = pill.select_one(".th").get_text(strip=True) if pill.select_one(".th") else ""
            sp = pill.select_one("span:not(.th)")
            txt = sp.get_text(strip=True) if sp else ""
            m_ph = re.match(r"\(([^)]+)\)\s*(.*)", txt)
            if m_ph:
                ph = m_ph.group(1).strip()
                mean = m_ph.group(2).strip()
            else:
                ph = ""
                mean = txt
            if th:
                examples.append({"thai": th, "phonetic": ph, "meaning": mean})
        
        grammar_list.append({
            "issue_code": issue_code,
            "point_num": idx,
            "title": g_title,
            "explanation_html": exp_html,
            "examples_json": json.dumps(examples, ensure_ascii=False)
        })

    # 4. Culture Section
    cult_card = soup.select_one(".culture-card")
    cult_title = ""
    cult_body_html = ""
    cult_memo_html = ""
    
    if cult_card:
        h3 = cult_card.select_one("h3")
        cult_title = h3.get_text(strip=True).replace("🏛️", "").strip() if h3 else ""
        
        body_ps = []
        for p in cult_card.find_all("p", recursive=False):
            body_ps.append(f"<p>{''.join([str(c) for c in p.contents]).strip()}</p>")
        cult_body_html = "\n".join(body_ps)
        
        callout = cult_card.select_one(".culture-callout")
        if callout:
            cult_memo_html = "".join([str(c) for c in callout.contents]).strip()
            
        # Culture Vocab items (if culture-vocab-sec exists)
        cult_sec = cult_card.select_one(".culture-vocab-sec")
        if cult_sec:
            for pill in cult_sec.select(".example-pill"):
                th = pill.select_one(".th").get_text(strip=True) if pill.select_one(".th") else ""
                sp = pill.select_one("span:not(.th)")
                txt = sp.get_text(strip=True) if sp else ""
                m_ph = re.match(r"\(([^)]+)\)\s*(.*)", txt)
                if m_ph:
                    ph = m_ph.group(1).strip()
                    mean = m_ph.group(2).strip()
                else:
                    ph = ""
                    mean = txt
                if th:
                    vocab_list.append({
                        "issue_code": issue_code,
                        "type": "culture",
                        "thai": th,
                        "phonetic": ph,
                        "meaning": mean
                    })

    # Email template info
    email_file = ROOT_DIR / f"email_{issue_code}.html"
    email_subject = f"【泰語學習週報】VOL. {issue_code} ｜ {title}"
    email_intro_html = ""
    email_highlights_html = ""
    if email_file.exists():
        e_soup = BeautifulSoup(email_file.read_text(encoding="utf-8"), "html.parser")
        e_intro = e_soup.select_one(".intro-text")
        if e_intro:
            email_intro_html = "".join([str(c) for c in e_intro.contents]).strip()
        e_card = e_soup.select_one(".highlight-card")
        if e_card:
            email_highlights_html = "".join([str(c) for c in e_card.contents if "highlight-title" not in getattr(c, "get", lambda x, y: "")("class", [])]).strip()

    issue_data = {
        "issue_code": issue_code,
        "year": year,
        "week": week,
        "publish_date": date_span,
        "status": "published",
        "title": title,
        "subtitle_1": subtitle_1,
        "subtitle_2": subtitle_2,
        "read_time": read_time,
        "highlights": highlights,
        "culture_title": cult_title,
        "culture_body_html": cult_body_html,
        "culture_memo_html": cult_memo_html,
        "email_subject": email_subject,
        "email_intro_html": email_intro_html,
        "email_highlights_html": email_highlights_html,
    }

    return {
        "issue": issue_data,
        "vocab": vocab_list,
        "sentences": sentences_list,
        "grammar": grammar_list,
    }

if __name__ == "__main__":
    for f in ["26w41.html", "26w42.html", "26w43.html"]:
        p = ROOT_DIR / f
        if p.exists():
            res = parse_lesson_file(p)
            print(f"=== {f} ===")
            print(f"Issue: {res['issue']['issue_code']} - {res['issue']['title']} ({res['issue']['publish_date']})")
            print(f"Vocab count: {len(res['vocab'])} (Core: {sum(1 for v in res['vocab'] if v['type']=='core')}, Cult: {sum(1 for v in res['vocab'] if v['type']=='culture')})")
            print(f"Sentences count: {len(res['sentences'])}")
            print(f"Grammar count: {len(res['grammar'])}")
