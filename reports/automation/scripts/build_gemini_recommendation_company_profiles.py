#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone, timedelta
import html, json, os, re, time, urllib.parse, urllib.request
import pandas as pd

try:
    from stock_news_disambiguation import is_etf_name, etf_theme, stock_basic_info, filter_and_rank_news, extract_publisher, format_pubdate
except Exception:
    is_etf_name = lambda name: False
    etf_theme = lambda name: "ETF"
    stock_basic_info = lambda name, sector="", reason="", price="", score="", entry="", news_rows=None: f"{name}: 기본 정보 확인 필요"
    filter_and_rank_news = None
    extract_publisher = lambda link='', originallink='', raw='': ''
    format_pubdate = lambda value: str(value or '')

KST = timezone(timedelta(hours=9))

def now(): return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")

def read_csv_safely(path):
    p = Path(path)
    if not p.exists(): return pd.DataFrame()
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try: return pd.read_csv(p, dtype=str, encoding=enc).fillna("")
        except Exception: pass
    return pd.DataFrame()

def write_csv_safely(df, path):
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    df.fillna("").to_csv(p, index=False, encoding="utf-8-sig")

def s(x):
    if x is None: return ""
    text = str(x).strip()
    return "" if text.lower() in {"nan", "none", "null", "nat"} else text

def clean(x): return re.sub(r"<.*?>", "", html.unescape(s(x)))

def get(row, *names):
    for n in names:
        if n in row and s(row.get(n)): return s(row.get(n))
    lower = {str(k).lower(): k for k in row.keys()}
    for n in names:
        k = lower.get(str(n).lower())
        if k and s(row.get(k)): return s(row.get(k))
    return ""

def related_news(news_df, name, code="", limit=3):
    if news_df.empty or not name: return []
    rows = [dict(r) for _, r in news_df.iterrows()]
    if filter_and_rank_news:
        return filter_and_rank_news(name, code, rows, limit=limit)
    return [r for r in rows if name in " ".join([get(r,"query"), get(r,"title"), get(r,"description")])][:limit]

def extract_json(text):
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"(\{.*\}|\[.*\])", text, re.S)
        if m: return json.loads(m.group(1))
        raise

def call_gemini(prompt):
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    primary = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash").strip() or "gemini-3.5-flash"
    models = []
    for m in [primary, "gemini-2.5-flash", "gemini-2.5-flash-lite"]:
        if m and m not in models: models.append(m)
    if not key: raise RuntimeError("GEMINI_API_KEY missing")
    last_error = None
    for model in models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{urllib.parse.quote(model)}:generateContent"
            payload = {
                "system_instruction": {"parts": [{"text": "당신은 한국 주식 투자자를 위한 리서치 요약 작성자입니다. 종목 설명은 단순 업종 반복이 아니라, 회사/ETF를 이해할 수 있는 투자 아이디어 노트로 작성합니다. 현재가, 점수, 진입판정처럼 이미 별도 표에 있는 수치는 반복하지 않습니다. 확실하지 않은 구성종목이나 시장점유율은 단정하지 말고 '확인 필요' 또는 '주요 노출 분야'로 표현합니다. 반드시 JSON만 출력하세요."}]},
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.35, "maxOutputTokens": 6000, "responseMimeType": "application/json"}
            }
            req = urllib.request.Request(url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), headers={"Content-Type":"application/json", "x-goog-api-key":key})
            with urllib.request.urlopen(req, timeout=60) as res:
                data = json.loads(res.read().decode("utf-8"))
            txt = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            obj = extract_json(txt)
            rows = obj.get("profiles") if isinstance(obj, dict) else obj
            if not isinstance(rows, list): raise RuntimeError("Gemini JSON profiles is not list")
            for r in rows:
                if isinstance(r, dict): r["gemini_model_used"] = model
            return [r for r in rows if isinstance(r, dict)]
        except Exception as e:
            last_error = e
            print(f"⚠️ Gemini recommendation profile failed: {model} :: {repr(e)}")
            time.sleep(1.0)
    raise RuntimeError(f"all Gemini models failed: {repr(last_error)}")

def build_prompt(candidates, news_df):
    items = []
    for idx, r in enumerate(candidates, start=1):
        name = get(r, "stock_name", "종목명")
        code = get(r, "stock_code", "종목코드")
        sector = get(r, "sector", "섹터/분야", "분야")
        is_etf = is_etf_name(name)
        news = related_news(news_df, name, code, 3)
        news_lines = []
        for n in news:
            title = clean(get(n, "title", "제목"))
            desc = clean(get(n, "description", "요약", "본문"))
            press = get(n, "publisher", "언론사") or extract_publisher(get(n, "link", "링크"), get(n, "originallink", "origin_link"))
            date = get(n, "published_at", "날짜") or format_pubdate(get(n, "pubDate"))
            news_lines.append(f"- {press} / {date} / {title} / {desc[:140]}")
        items.append({
            "rank": get(r, "rank", "순위") or str(idx),
            "stock_name": name,
            "stock_code": code,
            "sector": sector,
            "is_etf": is_etf,
            "etf_theme_hint": etf_theme(name) if is_etf else "",
            "entry_guide": get(r, "entry_guide", "진입가이드", "상세전략가이드"),
            "news": news_lines,
        })
    return f"""
아래 추천 종목들에 대해 사용자가 예시로 준 수준의 '미니 리서치 노트'를 작성하세요.

요구:
- 현재가, 실전점수, 진입판정, 익절/손절 수치는 이미 화면에 있으므로 반복하지 마세요.
- ETF는 어떤 컨셉의 상품인지, 어떤 산업/자산군에 노출되는지, 구성종목 또는 주요 노출 분야를 설명하세요.
- 개별 종목은 무엇을 만들고 파는지, 주요 고객사/전방산업, 최근 실적·공시·테마·수급 포인트를 설명하세요.
- '분석 컨셉', '한 줄 요약', '핵심 투자 포인트', '주의 리스크'가 보이게 작성하세요.
- 확실하지 않은 수치, 점유율, 구성종목은 단정하지 말고 '확인 필요', '주요 노출 분야'로 표현하세요.
- 조금 주절주절해도 괜찮지만 중복 정보는 제거하세요.

입력 종목:
{json.dumps(items, ensure_ascii=False, indent=2)}

반드시 아래 JSON 형식으로만 답하세요.
{{
  "profiles": [
    {{
      "stock_name": "종목명",
      "stock_code": "종목코드",
      "analysis_concept": "예: 체질 개선 및 전방 산업 모멘텀 추적",
      "one_line_summary": "한 줄 요약 1~2문장",
      "bull_points": ["핵심 투자 포인트 1", "핵심 투자 포인트 2", "핵심 투자 포인트 3"],
      "bear_points": ["주의 리스크 1", "주의 리스크 2"],
      "etf_or_business_details": "ETF면 주요 노출 분야/구성 확인 포인트, 개별주면 주요 제품/고객/사업 구조",
      "profile_text": "화면에 표시할 종합 설명. 5~9문장. 현재가/점수/진입판정 반복 금지"
    }}
  ]
}}
""".strip()

def fallback_profile(row, news_df):
    name = get(row, "stock_name", "종목명")
    code = get(row, "stock_code", "종목코드")
    sector = get(row, "sector", "섹터/분야", "분야")
    news = related_news(news_df, name, code, 2)
    base = stock_basic_info(name, sector, get(row, "entry_guide"), "", "", "", news)
    if is_etf_name(name):
        concept = f"{etf_theme(name)} 테마 ETF 분석"
        bull = ["테마 성장성", "분산 투자 효과", "구성종목·분배금 확인 필요"]
        bear = ["테마형 ETF 특유의 변동성", "실제 구성종목과 운용보수 확인 필요"]
        detail = "운용사 페이지에서 구성종목, 추종 또는 액티브 전략, 환율 영향, 분배금 정책을 확인해야 합니다."
    else:
        concept = "사업 구조와 업종 모멘텀 추적"
        bull = ["전방산업 회복 여부", "실적·수주·공시 변화", "거래량과 수급 개선 여부"]
        bear = ["업종 둔화 시 실적 동조화", "뉴스가 가격에 이미 반영됐을 가능성"]
        detail = "주요 제품, 고객사, 전방산업, 최근 실적 변화를 함께 확인해야 합니다."
    return {"stock_name":name, "stock_code":code, "analysis_concept":concept, "one_line_summary":base, "bull_points":bull, "bear_points":bear, "etf_or_business_details":detail, "profile_text":f"{base} {detail}", "gemini_model_used":"fallback"}

def profile_to_text(p):
    concept = s(p.get("analysis_concept"))
    one = s(p.get("one_line_summary"))
    details = s(p.get("etf_or_business_details"))
    bulls = p.get("bull_points") or []
    bears = p.get("bear_points") or []
    if isinstance(bulls, str): bulls = [bulls]
    if isinstance(bears, str): bears = [bears]
    bull_txt = " / ".join([s(x) for x in bulls if s(x)][:3])
    bear_txt = " / ".join([s(x) for x in bears if s(x)][:2])
    body = s(p.get("profile_text"))
    parts = []
    if concept: parts.append(f"🤖 분석 컨셉: {concept}")
    if one: parts.append(f"📌 한 줄 요약: {one}")
    if bull_txt: parts.append(f"🚀 핵심 포인트: {bull_txt}")
    if details: parts.append(f"📦 사업/구성 포인트: {details}")
    if bear_txt: parts.append(f"⚠️ 주의 리스크: {bear_txt}")
    if body and body not in " ".join(parts): parts.append(body)
    return "\n".join(parts).strip()

def update_csv_profiles(candidates, profiles):
    by_name = {s(p.get("stock_name")): p for p in profiles if s(p.get("stock_name"))}
    out = []
    for _, r in candidates.iterrows():
        row = dict(r)
        name = get(row, "stock_name", "종목명")
        p = by_name.get(name)
        if p:
            row["analysis_concept"] = s(p.get("analysis_concept"))
            row["one_line_summary"] = s(p.get("one_line_summary"))
            row["bull_points"] = " / ".join(p.get("bull_points") or []) if isinstance(p.get("bull_points"), list) else s(p.get("bull_points"))
            row["bear_points"] = " / ".join(p.get("bear_points") or []) if isinstance(p.get("bear_points"), list) else s(p.get("bear_points"))
            row["etf_or_business_details"] = s(p.get("etf_or_business_details"))
            row["stock_description"] = profile_to_text(p)
            row["profile_model"] = s(p.get("gemini_model_used"))
        out.append(row)
    return pd.DataFrame(out)

def build():
    data_dir = Path("docs/data")
    top_path = data_dir / "latest_recommendation_top15_full.csv"
    analysis_path = data_dir / "latest_recommendation_analysis.csv"
    news_path = data_dir / "latest_news_detail.csv"
    status_path = data_dir / "latest_recommendation_profile_status.csv"
    profile_path = data_dir / "latest_recommendation_company_profiles.csv"

    top = read_csv_safely(top_path)
    news = read_csv_safely(news_path)
    if top.empty:
        write_csv_safely(pd.DataFrame([{"status":"NO_TOP15", "checked_at":now()}]), status_path)
        print("⚠️ TOP15 data not found; skip Gemini recommendation profiles")
        return

    candidates = [dict(r) for _, r in top.head(15).iterrows()]
    try:
        profiles = call_gemini(build_prompt(candidates, news))
        status = {"status":"gemini_ok", "checked_at":now(), "rows":len(candidates), "profile_count":len(profiles)}
    except Exception as e:
        print(f"⚠️ Gemini recommendation profile fallback: {repr(e)}")
        profiles = [fallback_profile(r, news) for r in candidates]
        status = {"status":"fallback", "checked_at":now(), "rows":len(candidates), "profile_count":len(profiles), "error":repr(e)}

    names = {s(p.get("stock_name")) for p in profiles}
    for r in candidates:
        name = get(r, "stock_name", "종목명")
        if name and name not in names:
            profiles.append(fallback_profile(r, news))

    profile_rows = []
    for p in profiles:
        row = dict(p)
        if isinstance(row.get("bull_points"), list): row["bull_points"] = " / ".join([s(x) for x in row["bull_points"] if s(x)])
        if isinstance(row.get("bear_points"), list): row["bear_points"] = " / ".join([s(x) for x in row["bear_points"] if s(x)])
        row["profile_text_for_display"] = profile_to_text(p)
        row["checked_at"] = now()
        profile_rows.append(row)

    write_csv_safely(pd.DataFrame(profile_rows), profile_path)
    updated = update_csv_profiles(top, profiles)
    write_csv_safely(updated, top_path)
    write_csv_safely(updated, analysis_path)
    write_csv_safely(pd.DataFrame([status]), status_path)

    try:
        import publish_legacy_excel_sections
        publish_legacy_excel_sections.build_outputs()
        print("✅ legacy pages rebuilt with Gemini recommendation profiles")
    except Exception as e:
        print(f"⚠️ legacy page rebuild skipped: {repr(e)}")

    print("✅ Gemini recommendation company profiles built")
    print(f"profiles: {len(profile_rows)}")

if __name__ == "__main__":
    build()
