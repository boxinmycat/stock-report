#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clean HTML report builder v10.7
- Rebuilds docs/index.html and latest docs/reports/YYYYMMDD/index.html from the xlsx workbook.
- Prevents pandas Series artifacts such as "Name: 44, dtype: object" from leaking into HTML.
"""

from __future__ import annotations

import html
import math
import os
import re
import shutil
from pathlib import Path

import pandas as pd


def _clean_val(v):
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except Exception:
        pass
    if isinstance(v, float):
        if math.isnan(v):
            return ""
        if abs(v - round(v)) < 1e-9:
            return f"{int(round(v)):,}"
        return f"{v:,.2f}".rstrip("0").rstrip(".")
    if isinstance(v, int):
        return f"{v:,}"
    s = str(v)
    s = re.sub(r"\nName:\s*\d+,\s*dtype:\s*object", "", s)
    s = s.replace("NaN", "").replace("nan", "")
    return s.strip()


def _find_latest_xlsx() -> Path:
    candidates = []
    for pattern in ["docs/reports/**/20*.xlsx", "20*.xlsx", "stock_report/**/*.xlsx"]:
        candidates.extend(Path(".").glob(pattern))
    candidates = [p for p in candidates if p.is_file() and not p.name.startswith("~$")]
    if not candidates:
        raise FileNotFoundError("xlsx 리포트 파일을 찾지 못했습니다.")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _read_sheet_header(xlsx_path: Path, sheet_name: str, header_candidates=None, max_scan: int = 25) -> pd.DataFrame:
    header_candidates = header_candidates or []
    try:
        preview = pd.read_excel(xlsx_path, sheet_name=sheet_name, header=None, nrows=max_scan, engine="openpyxl")
    except ValueError:
        return pd.DataFrame()

    header_row = 0
    best_score = -1
    for i, row in preview.iterrows():
        vals = [_clean_val(v) for v in row.tolist() if _clean_val(v)]
        score = 0
        for cand in header_candidates:
            if any(cand in v for v in vals):
                score += 1
        if score > best_score:
            best_score = score
            header_row = i

    if best_score <= 0 and header_candidates:
        header_row = 0

    try:
        df = pd.read_excel(xlsx_path, sheet_name=sheet_name, header=header_row, engine="openpyxl")
    except Exception:
        return pd.DataFrame()

    df.columns = [_clean_val(c) for c in df.columns]
    df = df.loc[:, [c for c in df.columns if c]]
    df = df.dropna(how="all").dropna(axis=1, how="all")
    return df


def _find_col(df: pd.DataFrame, candidates) -> str | None:
    for c in df.columns:
        cs = str(c).replace(" ", "")
        for cand in candidates:
            if cand.replace(" ", "") in cs:
                return c
    return None


def _table_html(df: pd.DataFrame, cols=None, limit=12) -> str:
    if df is None or df.empty:
        return '<p class="muted">표시할 데이터가 없습니다.</p>'
    if cols:
        use = [c for c in cols if c in df.columns]
        if not use:
            use = list(df.columns[: min(8, len(df.columns))])
        df = df[use]
    else:
        df = df.iloc[:, : min(8, df.shape[1])]
    if limit:
        df = df.head(limit)

    out = ['<div class="table-wrap"><table class="data-table"><thead><tr>']
    for c in df.columns:
        out.append(f"<th>{html.escape(_clean_val(c))}</th>")
    out.append("</tr></thead><tbody>")

    for _, row in df.iterrows():
        out.append("<tr>")
        for v in row:
            out.append(f"<td>{html.escape(_clean_val(v)).replace(chr(10), '<br>')}</td>")
        out.append("</tr>")

    out.append("</tbody></table></div>")
    return "".join(out)


def _key_value_cards(df: pd.DataFrame, kcol: str = "구분", vcol: str = "내용", max_items: int = 10) -> str:
    if df is None or df.empty:
        return '<p class="muted">표시할 데이터가 없습니다.</p>'
    if kcol not in df.columns:
        kcol = df.columns[0]
    if vcol not in df.columns:
        vcol = df.columns[1] if len(df.columns) > 1 else df.columns[0]

    cards = []
    for _, row in df.head(max_items).iterrows():
        k = _clean_val(row.get(kcol, ""))
        v = _clean_val(row.get(vcol, ""))
        if not k and not v:
            continue
        cards.append(
            f'<div class="metric"><div class="label">{html.escape(k)}</div>'
            f'<div class="value">{html.escape(v).replace(chr(10), "<br>")}</div></div>'
        )
    return '<div class="metrics">' + "".join(cards) + "</div>"


def _session_label() -> str:
    mode = os.getenv("REPORT_RUN_MODE", "").strip()
    if mode == "AM_PREMARKET":
        return "장전 08:35 리포트"
    if mode == "PM_CLOSE":
        return "장마감 16:05 리포트"
    return "자동 리포트"


def build_clean_report(xlsx_path: Path | None = None) -> Path:
    xlsx_path = Path(xlsx_path) if xlsx_path else _find_latest_xlsx()
    m = re.search(r"(20\d{6})", xlsx_path.name)
    report_date = m.group(1) if m else pd.Timestamp.now(tz="Asia/Seoul").strftime("%Y%m%d")
    pretty = f"{report_date[:4]}-{report_date[4:6]}-{report_date[6:]}"

    report_dir = Path("docs") / "reports" / report_date
    report_dir.mkdir(parents=True, exist_ok=True)

    # Keep the workbook next to the page.
    target_xlsx = report_dir / xlsx_path.name
    if xlsx_path.resolve() != target_xlsx.resolve():
        shutil.copy2(xlsx_path, target_xlsx)

    market = _read_sheet_header(target_xlsx, "시장브리핑", ["구분", "내용", "해석"])
    top = _read_sheet_header(target_xlsx, "TOP후보_요약", ["순위", "종목명"])
    cont = _read_sheet_header(target_xlsx, "연속추천_관찰", ["주목등급", "종목명"])
    scen = _read_sheet_header(target_xlsx, "진입시나리오", ["순위", "종목명", "진입판정"])
    acct = _read_sheet_header(target_xlsx, "계좌백테스트요약", ["누적수익률", "MDD"])
    news_sum = _read_sheet_header(target_xlsx, "네이버뉴스_요약", ["구분", "요약"])
    news_detail = _read_sheet_header(target_xlsx, "네이버뉴스_상세", ["query", "title"])
    holdings = _read_sheet_header(target_xlsx, "보유종목_관리", ["종목명", "보유수량", "평균단가"])
    trade_log = _read_sheet_header(target_xlsx, "매매기록_관리", ["거래일", "구분", "종목명"])

    if news_sum.empty:
        news_detail = _read_sheet_header(target_xlsx, "뉴스이슈", ["query", "title"])

    name_col = _find_col(top, ["종목명"])
    score_col = _find_col(top, ["실전점수", "점수"])
    sector_col = _find_col(top, ["섹터", "분야"])
    entry_col = _find_col(top, ["진입판정"])

    stock_cards = []
    for _, row in top.head(6).iterrows():
        name = _clean_val(row.get(name_col, "")) if name_col else ""
        score = _clean_val(row.get(score_col, "")) if score_col else ""
        sector = _clean_val(row.get(sector_col, "")) if sector_col else ""
        entry = _clean_val(row.get(entry_col, "")) if entry_col else "조건 확인 후 진입"
        rank = _clean_val(row.get("순위", ""))
        stock_cards.append(
            f'<article class="stock-card"><div class="rank">#{html.escape(rank or "-")}</div>'
            f"<h3>{html.escape(name)}</h3><p class=\"muted\">{html.escape(sector)}</p>"
            f'<div class="pill">실전점수 {html.escape(score or "-")}</div>'
            f"<p>{html.escape(entry or '조건 확인 후 진입')}</p></article>"
        )

    news_block = _table_html(news_sum, limit=12) if not news_sum.empty else _table_html(
        news_detail, cols=["query", "title", "description", "pubDate", "link"], limit=10
    )

    css = """
:root{--bg:#f5f7fb;--card:#fff;--ink:#111827;--muted:#64748b;--line:#e5e7eb;--blue:#1d4ed8;--dark:#0f172a}
*{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans KR",Arial,sans-serif;line-height:1.55}
header{background:linear-gradient(135deg,#0f172a,#1e40af);color:#fff;padding:34px 22px 42px}.wrap{max-width:1180px;margin:0 auto}
h1{margin:0;font-size:30px}h2{font-size:22px;margin:0 0 16px}h3{margin:4px 0 8px}.subtitle{opacity:.88;margin-top:8px}
.section{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:22px;margin:18px auto;box-shadow:0 8px 24px rgba(15,23,42,.06)}
.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}.metric{background:#f8fafc;border:1px solid #e2e8f0;border-radius:14px;padding:14px}.label{font-size:13px;color:var(--muted)}.value{font-size:17px;font-weight:700;margin-top:6px}
.stock-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px}.stock-card{border:1px solid var(--line);border-radius:16px;background:#fff;padding:16px}.rank{font-weight:800;color:var(--blue)}.pill{display:inline-block;background:#eff6ff;color:#1d4ed8;border-radius:999px;padding:4px 10px;font-size:13px;font-weight:700}
.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:14px}.data-table{width:100%;border-collapse:collapse;background:#fff;font-size:14px}.data-table th{background:#f1f5f9;text-align:left;color:#334155}.data-table th,.data-table td{border-bottom:1px solid #e5e7eb;padding:10px 12px;vertical-align:top}.data-table tr:last-child td{border-bottom:0}
.muted{color:var(--muted)}.note{background:#fffbeb;border-left:4px solid #f59e0b;padding:12px 14px;border-radius:10px}.links a{display:inline-block;margin:4px 8px 4px 0;color:#1d4ed8;text-decoration:none;font-weight:700}footer{color:#64748b;text-align:center;padding:30px}
"""

    body = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>실전매매 리포트 {pretty}</title><style>{css}</style></head><body>
<header><div class="wrap"><h1>실전매매 리포트 · {pretty}</h1><div class="subtitle">{html.escape(_session_label())} · 클린 HTML v10.7</div></div></header>
<main class="wrap">
<section class="section"><h2>오늘 시장브리핑</h2>{_key_value_cards(market)}<p class="note">이 리포트는 자동 후보 선별과 참고용 해석 자료입니다. 실제 매수는 체결가·거래량·호가·손절 기준을 확인한 뒤 판단하는 쪽이 안전합니다.</p></section>
<section class="section"><h2>TOP 후보 핵심 카드</h2><div class="stock-grid">{''.join(stock_cards) if stock_cards else '<p class="muted">TOP 후보 데이터가 없습니다.</p>'}</div></section>
<section class="section"><h2>TOP 후보 요약표</h2>{_table_html(top, cols=['순위','종목명','시장','섹터/분야','후보출처','현재가','기본점수','실전점수','과열판정','진입판정'], limit=15)}</section>
<section class="section"><h2>네이버 주요 뉴스 요약</h2>{news_block}</section>
<section class="section"><h2>내 보유종목 관리</h2>{_table_html(holdings, cols=['상태','종목명','종목코드','보유수량','평균단가','현재가','평가손익','수익률(%)','목표가','손절가','리포트상태','관리메모'], limit=20)}<p class="muted">보유종목은 보유종목_수동입력.csv를 기준으로 표시됩니다. 공개 저장소라면 수량·평균단가가 노출될 수 있으니 주의하세요.</p></section>
<section class="section"><h2>연속추천 관찰</h2>{_table_html(cont, limit=15)}</section>
<section class="section"><h2>진입 시나리오</h2>{_table_html(scen, cols=['순위','종목명','섹터/분야','현재가','진입판정','공격진입가','기준진입가','보수진입가','손절기준가'], limit=15)}</section>
<section class="section"><h2>계좌 백테스트 요약</h2>{_table_html(acct, limit=5)}</section>
<section class="section links"><h2>파일</h2><a href="{html.escape(target_xlsx.name)}">엑셀 리포트 다운로드</a></section>
</main><footer>Generated by stock-report automation · rebuild_clean_html_report.py</footer></body></html>"""

    (report_dir / "index.html").write_text(body, encoding="utf-8")
    Path("docs").mkdir(exist_ok=True)
    (Path("docs") / "index.html").write_text(body, encoding="utf-8")
    print(f"✅ Clean HTML rebuilt: {report_dir / 'index.html'}")
    return report_dir / "index.html"


if __name__ == "__main__":
    build_clean_report()
