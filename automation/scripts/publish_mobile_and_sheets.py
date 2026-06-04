#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v10.9 Mobile + Google Sheets publisher
- Copies the latest HTML briefing to docs/latest/index.html for mobile access.
- Builds docs/mobile/index.html as a simple phone-friendly landing page.
- Exports latest CSV files under docs/data/ for Google Sheets IMPORTDATA.

This script is intentionally defensive: if one sheet/file is missing, it still
publishes whatever data is available instead of failing the whole workflow.
"""
from __future__ import annotations

import csv
import html
import os
import re
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import pandas as pd
except Exception as e:  # pragma: no cover
    print(f"⚠️ pandas import failed: {e}")
    pd = None

KST = timezone(timedelta(hours=9))
ROOT = Path(".")
DOCS = ROOT / "docs"
DATA = DOCS / "data"
LATEST = DOCS / "latest"
MOBILE = DOCS / "mobile"
REPORTS = DOCS / "reports"

SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "https://boxinmycat.github.io/stock-report").rstrip("/")


def now_kst() -> datetime:
    return datetime.now(KST)


def current_session() -> str:
    env = os.environ.get("REPORT_SESSION", "").upper().strip()
    if env in {"AM", "PM", "MANUAL"}:
        return env
    hour = now_kst().hour
    if hour < 12:
        return "AM"
    return "PM"


def safe_text(value) -> str:
    if value is None:
        return ""
    try:
        if pd is not None and pd.isna(value):
            return ""
    except Exception:
        pass
    s = str(value)
    # Remove pandas Series artifacts if any cell accidentally contains them.
    s = re.sub(r"\n?Name:\s*\d+.*?dtype:\s*object", "", s, flags=re.S)
    s = s.replace("nan", "") if s.strip().lower() == "nan" else s
    return s.strip()


def normalize_code(value) -> str:
    s = safe_text(value)
    if not s:
        return ""
    # Preserve ETF codes such as 0155N0; otherwise zero-fill numeric stock codes.
    s = s.replace(".0", "") if re.fullmatch(r"\d+\.0", s) else s
    if re.fullmatch(r"\d{1,6}", s):
        return s.zfill(6)
    return s


def write_csv(path: Path, rows: list[dict], headers: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({h: safe_text(row.get(h, "")) for h in headers})
    print(f"✅ CSV published: {path} ({len(rows)} rows)")


def read_csv_flexible(path: Path) -> list[dict]:
    if not path.exists():
        return []
    encodings = ["utf-8-sig", "utf-8", "cp949", "euc-kr"]
    last_error = None
    for enc in encodings:
        try:
            with path.open("r", encoding=enc, newline="") as f:
                return list(csv.DictReader(f))
        except Exception as e:
            last_error = e
    print(f"⚠️ CSV read failed: {path} / {last_error}")
    return []


def find_latest_xlsx() -> Path | None:
    candidates = [p for p in ROOT.glob("*.xlsx") if not p.name.startswith("~$")]
    if not candidates:
        candidates = [p for p in ROOT.glob("**/*.xlsx") if not p.name.startswith("~$")]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def read_sheet_rows(xlsx: Path | None, sheet_candidates: list[str], max_rows: int = 50) -> list[dict]:
    if pd is None or xlsx is None or not xlsx.exists():
        return []
    try:
        xl = pd.ExcelFile(xlsx)
    except Exception as e:
        print(f"⚠️ Excel open failed: {xlsx} / {e}")
        return []
    sheet_name = None
    for cand in sheet_candidates:
        if cand in xl.sheet_names:
            sheet_name = cand
            break
    if not sheet_name:
        return []
    try:
        df = pd.read_excel(xlsx, sheet_name=sheet_name)
    except Exception as e:
        print(f"⚠️ Sheet read failed: {sheet_name} / {e}")
        return []
    df = df.dropna(how="all").head(max_rows)
    rows = []
    for _, r in df.iterrows():
        item = {safe_text(k): safe_text(v) for k, v in r.to_dict().items() if safe_text(k)}
        if any(item.values()):
            rows.append(item)
    return rows


def pick(row: dict, names: list[str]) -> str:
    normalized = {str(k).replace(" ", "").lower(): v for k, v in row.items()}
    for name in names:
        key = name.replace(" ", "").lower()
        if key in normalized:
            return safe_text(normalized[key])
    # contains fallback
    for name in names:
        key = name.replace(" ", "").lower()
        for k, v in normalized.items():
            if key and key in k:
                return safe_text(v)
    return ""


def export_holdings() -> None:
    rows = read_csv_flexible(ROOT / "holdings_manual_input.csv")
    if not rows:
        rows = read_csv_flexible(ROOT / "보유종목_수동입력.csv")
    out = []
    for r in rows:
        out.append({
            "status": pick(r, ["status", "상태"]),
            "stock_name": pick(r, ["stock_name", "종목명", "종목"]),
            "stock_code": normalize_code(pick(r, ["stock_code", "종목코드", "코드"])),
            "quantity": pick(r, ["quantity", "보유수량", "수량"]),
            "avg_price": pick(r, ["avg_price", "평균단가", "평단"]),
            "buy_date": pick(r, ["buy_date", "매수일"]),
            "target_price": pick(r, ["target_price", "목표가"]),
            "stop_loss": pick(r, ["stop_loss", "손절가"]),
            "memo": pick(r, ["memo", "메모"]),
        })
    headers = ["status", "stock_name", "stock_code", "quantity", "avg_price", "buy_date", "target_price", "stop_loss", "memo"]
    write_csv(DATA / "latest_holdings.csv", out, headers)


def export_trades() -> None:
    rows = read_csv_flexible(ROOT / "trade_log_manual_input.csv")
    if not rows:
        rows = read_csv_flexible(ROOT / "매매기록_수동입력.csv")
    out = []
    for r in rows:
        out.append({
            "trade_date": pick(r, ["trade_date", "거래일"]),
            "trade_type": pick(r, ["trade_type", "구분"]),
            "stock_name": pick(r, ["stock_name", "종목명", "종목"]),
            "stock_code": normalize_code(pick(r, ["stock_code", "종목코드", "코드"])),
            "quantity": pick(r, ["quantity", "수량"]),
            "price": pick(r, ["price", "단가"]),
            "fee": pick(r, ["fee", "수수료"]),
            "tax": pick(r, ["tax", "세금"]),
            "memo": pick(r, ["memo", "메모"]),
        })
    headers = ["trade_date", "trade_type", "stock_name", "stock_code", "quantity", "price", "fee", "tax", "memo"]
    write_csv(DATA / "latest_trade_log.csv", out, headers)


def export_candidates(xlsx: Path | None) -> None:
    source_rows = read_sheet_rows(xlsx, ["TOP후보_요약", "추천 리스트", "추천리스트"], max_rows=30)
    out = []
    for i, r in enumerate(source_rows, 1):
        out.append({
            "rank": pick(r, ["순위", "rank"]) or str(i),
            "stock_name": pick(r, ["종목명", "종목", "stock_name"]),
            "stock_code": normalize_code(pick(r, ["종목코드", "코드", "stock_code"])),
            "score": pick(r, ["점수", "종합점수", "score"]),
            "sector": pick(r, ["섹터", "분야", "sector"]),
            "signal": pick(r, ["신호", "추천", "매수", "signal"]),
            "memo": pick(r, ["메모", "요약", "사유", "memo"]),
        })
    headers = ["rank", "stock_name", "stock_code", "score", "sector", "signal", "memo"]
    write_csv(DATA / "latest_candidates.csv", out, headers)


def export_news(xlsx: Path | None) -> None:
    source_rows = read_sheet_rows(xlsx, ["네이버뉴스_요약", "NaverNewsSummary", "news_summary"], max_rows=100)
    out = []
    for r in source_rows:
        out.append({
            "category": pick(r, ["구분", "분류", "category"]),
            "keyword": pick(r, ["키워드", "종목", "keyword", "stock_name"]),
            "title": pick(r, ["제목", "title"]),
            "summary": pick(r, ["요약", "description", "summary"]),
            "link": pick(r, ["링크", "link", "url"]),
            "published_at": pick(r, ["일시", "날짜", "published_at"]),
        })
    headers = ["category", "keyword", "title", "summary", "link", "published_at"]
    write_csv(DATA / "latest_news_summary.csv", out, headers)


def latest_report_dir() -> Path | None:
    if not REPORTS.exists():
        return None
    dirs = [p for p in REPORTS.iterdir() if p.is_dir() and (p / "index.html").exists()]
    if not dirs:
        return None
    return max(dirs, key=lambda p: (p / "index.html").stat().st_mtime)


def publish_latest_page() -> str:
    LATEST.mkdir(parents=True, exist_ok=True)
    latest_dir = latest_report_dir()
    source = None
    if latest_dir and (latest_dir / "index.html").exists():
        source = latest_dir / "index.html"
    elif (DOCS / "index.html").exists():
        source = DOCS / "index.html"
    if source:
        shutil.copyfile(source, LATEST / "index.html")
        print(f"✅ Latest mobile report copied: {source} -> {LATEST / 'index.html'}")
    else:
        (LATEST / "index.html").write_text("<h1>Stock Report</h1><p>No report has been generated yet.</p>", encoding="utf-8")
    return f"{SITE_BASE_URL}/latest/"


def create_root_redirect(latest_url: str) -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    html_text = f"""<!doctype html>
<html lang=\"ko\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>Stock Report</title>
  <meta http-equiv=\"refresh\" content=\"0; url=./latest/\">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 28px; line-height: 1.6; }}
    a {{ color: #0b57d0; font-weight: 700; }}
  </style>
</head>
<body>
  <h1>Stock Report</h1>
  <p>최신 리포트로 이동 중입니다.</p>
  <p><a href=\"./latest/\">최신 리포트 바로 열기</a></p>
  <p><a href=\"./mobile/\">모바일 메뉴 열기</a></p>
</body>
</html>
"""
    (DOCS / "index.html").write_text(html_text, encoding="utf-8")
    print("✅ Root index redirect created: docs/index.html -> ./latest/")


def create_mobile_landing(latest_url: str, session: str, xlsx: Path | None) -> None:
    MOBILE.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    generated = now_kst().strftime("%Y-%m-%d %H:%M:%S KST")
    xlsx_name = xlsx.name if xlsx else ""
    cards = [
        ("최신 리포트", "방금 생성된 장전/장마감 리포트", "../latest/"),
        ("추천후보 CSV", "Google Sheets 연동용", "../data/latest_candidates.csv"),
        ("보유종목 CSV", "현재 보유상태", "../data/latest_holdings.csv"),
        ("매매기록 CSV", "거래 히스토리", "../data/latest_trade_log.csv"),
        ("뉴스요약 CSV", "네이버뉴스 요약", "../data/latest_news_summary.csv"),
        ("v11 대시보드", "성과검증 + 보유판단", "../v11_dashboard/"),
        ("보유판단 CSV", "Google Sheets 연동용", "../data/latest_holding_judgment.csv"),
        ("진입가이드 CSV", "익절/손절 가이드", "../data/latest_entry_exit_guide.csv"),
        ("추천성과 CSV", "추천 후 성과 추적", "../data/latest_performance.csv"),
    ]
    card_html = "\n".join(
        f"<a class='card' href='{html.escape(url)}'><strong>{html.escape(title)}</strong><span>{html.escape(desc)}</span></a>"
        for title, desc, url in cards
    )
    mobile_html = f"""<!doctype html>
<html lang=\"ko\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>Stock Report Mobile</title>
  <style>
    body {{ margin:0; background:#f5f7fb; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; color:#111827; }}
    .wrap {{ max-width:760px; margin:0 auto; padding:22px 16px 40px; }}
    .hero {{ background:#111827; color:white; border-radius:22px; padding:22px; box-shadow:0 12px 28px rgba(15,23,42,.18); }}
    .hero h1 {{ margin:0 0 8px; font-size:26px; }}
    .hero p {{ margin:4px 0; color:#d1d5db; }}
    .grid {{ display:grid; gap:12px; margin-top:18px; }}
    .card {{ display:block; text-decoration:none; color:#111827; background:white; border-radius:18px; padding:18px; box-shadow:0 6px 18px rgba(15,23,42,.08); }}
    .card strong {{ display:block; font-size:18px; margin-bottom:6px; }}
    .card span {{ color:#6b7280; font-size:14px; }}
    .note {{ font-size:13px; color:#6b7280; margin-top:18px; line-height:1.55; }}
    code {{ background:#e5e7eb; padding:2px 5px; border-radius:6px; }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <section class=\"hero\">
      <h1>Stock Report</h1>
      <p>Session: {html.escape(session)}</p>
      <p>Updated: {html.escape(generated)}</p>
      <p>Source Excel: {html.escape(xlsx_name)}</p>
    </section>
    <section class=\"grid\">
      {card_html}
    </section>
    <p class=\"note\">휴대폰에서는 이 페이지를 크롬/사파리에서 열고 홈 화면에 추가해두면 편합니다. GitHub 앱에서 HTML을 열면 코드로 보일 수 있습니다.</p>
  </div>
</body>
</html>
"""
    (MOBILE / "index.html").write_text(mobile_html, encoding="utf-8")
    print("✅ Mobile landing page created: docs/mobile/index.html")


def export_summary(latest_url: str, session: str, xlsx: Path | None) -> None:
    rows = [{
        "generated_at_kst": now_kst().strftime("%Y-%m-%d %H:%M:%S"),
        "session": session,
        "latest_report_url": latest_url,
        "mobile_url": f"{SITE_BASE_URL}/mobile/",
        "source_excel": xlsx.name if xlsx else "",
        "candidates_csv": f"{SITE_BASE_URL}/data/latest_candidates.csv",
        "holdings_csv": f"{SITE_BASE_URL}/data/latest_holdings.csv",
        "trade_log_csv": f"{SITE_BASE_URL}/data/latest_trade_log.csv",
        "news_csv": f"{SITE_BASE_URL}/data/latest_news_summary.csv",
        "v11_dashboard_url": f"{SITE_BASE_URL}/v11_dashboard/",
        "holding_judgment_csv": f"{SITE_BASE_URL}/data/latest_holding_judgment.csv",
        "entry_exit_guide_csv": f"{SITE_BASE_URL}/data/latest_entry_exit_guide.csv",
        "performance_csv": f"{SITE_BASE_URL}/data/latest_performance.csv",
    }]
    headers = list(rows[0].keys())
    write_csv(DATA / "latest_report_summary.csv", rows, headers)


def create_sheets_formula_guide() -> None:
    text = f"""Google Sheets IMPORTDATA formulas

아래 수식을 구글 스프레드시트 각 시트의 A1 셀에 붙여넣으면 됩니다.
저장소/GitHub Pages가 공개 접근 가능해야 IMPORTDATA가 정상 작동합니다.

1) 추천후보
=IMPORTDATA(\"{SITE_BASE_URL}/data/latest_candidates.csv\")

2) 보유종목
=IMPORTDATA(\"{SITE_BASE_URL}/data/latest_holdings.csv\")

3) 매매기록
=IMPORTDATA(\"{SITE_BASE_URL}/data/latest_trade_log.csv\")

4) 네이버뉴스 요약
=IMPORTDATA(\"{SITE_BASE_URL}/data/latest_news_summary.csv\")

5) 최신 리포트 정보
=IMPORTDATA(\"{SITE_BASE_URL}/data/latest_report_summary.csv\")
"""
    (DOCS / "GOOGLE_SHEETS_IMPORTDATA_FORMULAS.txt").write_text(text, encoding="utf-8")
    print("✅ Google Sheets formula guide created")


def main() -> int:
    DOCS.mkdir(exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    session = current_session()
    xlsx = find_latest_xlsx()
    print(f"📱 v10.9 publish mobile/sheets start / session={session} / xlsx={xlsx}")

    export_candidates(xlsx)
    export_holdings()
    export_trades()
    export_news(xlsx)

    latest_url = publish_latest_page()
    create_root_redirect(latest_url)
    create_mobile_landing(latest_url, session, xlsx)
    export_summary(latest_url, session, xlsx)
    create_sheets_formula_guide()

    print("✅ v10.9 mobile + sheets publish completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
