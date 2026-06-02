#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rebuild clean HTML briefing report from the latest generated Excel file.

Purpose:
- Prevent pandas Series / NaN / dtype text from leaking into HTML briefing pages.
- Keep Excel as the source of truth.
- Generate clean docs/index.html and docs/reports/YYYYMMDD/index.html.

Run after the notebook execution step and before "Commit generated report".
"""

from __future__ import annotations

import html
import math
import os
import re
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd


def find_latest_xlsx() -> Path:
    candidates = []
    candidates += list(Path(".").glob("20*.xlsx"))
    candidates += list(Path("docs/reports").glob("*/20*.xlsx"))
    candidates += list(Path("stock_report").glob("**/20*.xlsx"))
    candidates = [p for p in candidates if p.is_file() and not p.name.startswith("~$")]
    if not candidates:
        raise FileNotFoundError("생성된 20*.xlsx 리포트 파일을 찾지 못했습니다.")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def clean_val(v) -> str:
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except Exception:
        pass

    if isinstance(v, float):
        if math.isfinite(v) and abs(v - int(v)) < 1e-9:
            return str(int(v))
        return f"{v:.2f}".rstrip("0").rstrip(".")

    s = str(v)
    if s.lower() == "nan":
        return ""

    # pandas Series 문자열이 들어온 경우 방어적으로 제거
    s = re.sub(r"\n?Name:\s*\d+,\s*dtype:\s*object", "", s)
    s = re.sub(r"(?m)^\s*NaN\s*$", "", s)
    s = re.sub(r"\n{3,}", "\n\n", s).strip()
    return s


def esc(v) -> str:
    return html.escape(clean_val(v)).replace("\n", "<br>")


def read_header_sheet(xlsx_path: Path, sheet: str) -> pd.DataFrame:
    try:
        df = pd.read_excel(xlsx_path, sheet_name=sheet, header=None, dtype=object)
    except Exception:
        return pd.DataFrame()

    if df.empty:
        return pd.DataFrame()

    header_idx = 0
    common_headers = {"순위", "종목명", "구분", "조회키", "주목등급", "query", "title"}

    for i in range(min(15, len(df))):
        non_empty = df.iloc[i].notna().sum()
        row_vals = {clean_val(x) for x in df.iloc[i].dropna().tolist()}
        if non_empty >= 2 and (row_vals & common_headers):
            header_idx = i
            break

    headers = [clean_val(x) or f"col{j}" for j, x in enumerate(df.iloc[header_idx].tolist())]
    out = df.iloc[header_idx + 1 :].copy()
    out.columns = headers
    out = out.dropna(how="all")
    return out


def table_html(headers, rows, cls="data-table") -> str:
    out = [f'<div class="table-wrap"><table class="{cls}"><thead><tr>']
    for h in headers:
        out.append(f"<th>{esc(h)}</th>")
    out.append("</tr></thead><tbody>")

    for row in rows:
        out.append("<tr>")
        for v in row:
            out.append(f"<td>{esc(v)}</td>")
        out.append("</tr>")

    out.append("</tbody></table></div>")
    return "".join(out)


def build_html(xlsx_path: Path) -> str:
    # 날짜 키 추출
    m = re.search(r"(20\d{6})", xlsx_path.name)
    date_key = m.group(1) if m else datetime.now().strftime("%Y%m%d")

    try:
        market = pd.read_excel(xlsx_path, sheet_name="시장브리핑", header=None, dtype=object)
    except Exception:
        market = pd.DataFrame()

    brief_rows = []
    sector_rows = []

    if not market.empty:
        for _, row in market.iloc[3:9].iterrows():
            brief_rows.append([clean_val(row.get(i, "")) for i in range(4)])

        for _, row in market.iloc[13:].iterrows():
            a = clean_val(row.get(0, ""))
            b = clean_val(row.get(1, ""))
            if a and b:
                sector_rows.append((a, b))

    top = read_header_sheet(xlsx_path, "TOP후보_요약")
    cont = read_header_sheet(xlsx_path, "연속추천_관찰")
    news = read_header_sheet(xlsx_path, "뉴스이슈")
    lab = read_header_sheet(xlsx_path, "실험실_요약")

    kpis = {}
    for row in brief_rows:
        if row and row[0]:
            kpis[row[0]] = row[1]

    market_mode = kpis.get("시장모드", "-")
    candidate_count = kpis.get("분석 후보 수", str(max(len(top), 0)))
    top_name = kpis.get("상위 후보", "-")
    hot_count = kpis.get("과열 후보 수", "-")

    brief_table = table_html(["구분", "내용", "해석/활용", "메모"], brief_rows) if brief_rows else '<p class="empty">시장브리핑 데이터 없음</p>'
    sector_html = "".join([f'<span class="chip">{esc(a)} <b>{esc(b)}</b></span>' for a, b in sector_rows]) or '<p class="empty">섹터 데이터 없음</p>'

    cards = []
    if not top.empty:
        for _, r in top.head(15).iterrows():
            rank = clean_val(r.get("순위", ""))
            name = clean_val(r.get("종목명", ""))
            sector = clean_val(r.get("섹터/분야", ""))
            source = clean_val(r.get("후보출처", ""))
            price = clean_val(r.get("현재가", ""))
            score = clean_val(r.get("실전점수", r.get("기본점수", "")))
            heat = clean_val(r.get("과열판정", ""))
            trend = clean_val(r.get("추세", ""))
            finance = clean_val(r.get("재무", ""))
            alloc = clean_val(r.get("추천투입금액", ""))
            decision = clean_val(r.get("판정", "조건 확인 후 진입"))
            guide = clean_val(r.get("상세전략가이드", ""))

            cards.append(f"""
    <article class="stock-card">
      <div class="stock-head">
        <div><span class="rank">#{esc(rank)}</span><h2>{esc(name)}</h2><p class="sub">{esc(sector)} · {esc(source)}</p></div>
        <span class="badge {'good' if heat == '정상' else 'warn'}">{esc(decision)}</span>
      </div>
      <div class="metric-grid">
        <div><label>현재가</label><strong>{esc(price)}원</strong></div>
        <div><label>실전점수</label><strong>{esc(score)}</strong></div>
        <div><label>과열</label><strong>{esc(heat)}</strong></div>
        <div><label>추천투입금액</label><strong>{esc(alloc)}원</strong></div>
      </div>
      <div class="mini-grid">
        <p><label>추세</label>{esc(trend)}</p>
        <p><label>재무</label>{esc(finance)}</p>
      </div>
      <p class="guide">{esc(guide)}</p>
    </article>""")

    cont_cols = ["주목등급", "종목명", "표시분야", "오늘순위", "오늘점수", "연속추천일수", "최근7회추천횟수", "최근등장흐름", "후보출처", "메모"]
    cont_rows = []
    if not cont.empty:
        for _, r in cont.head(15).iterrows():
            cont_rows.append([r.get(c, "") for c in cont_cols])
    cont_table = table_html(cont_cols, cont_rows) if cont_rows else '<p class="empty">연속추천 데이터 없음</p>'

    lab_rows = []
    if not lab.empty:
        lab2 = lab.copy()
        for col in ["전략수익률", "보유상승률", "MDD", "승률", "거래횟수"]:
            if col in lab2.columns:
                lab2[col] = pd.to_numeric(lab2[col], errors="coerce")
        sort_cols = [c for c in ["전략수익률", "보유상승률"] if c in lab2.columns]
        if sort_cols:
            lab2 = lab2.sort_values(sort_cols, ascending=False)
        if "종목명" in lab2.columns:
            lab2 = lab2.drop_duplicates(subset=["종목명"], keep="first")
        lab_cols = ["종목명", "기간선택", "전략콤보", "현재가", "보유상승률", "전략수익률", "MDD", "승률", "거래횟수"]
        for _, r in lab2.head(15).iterrows():
            lab_rows.append([r.get(c, "") for c in lab_cols])
    else:
        lab_cols = ["종목명", "기간선택", "전략콤보", "현재가", "보유상승률", "전략수익률", "MDD", "승률", "거래횟수"]
    lab_table = table_html(lab_cols, lab_rows) if lab_rows else '<p class="empty">백테스트 요약 데이터 없음</p>'

    news_cols = ["query", "title", "description"]
    news_rows = []
    if not news.empty:
        for _, r in news.head(10).iterrows():
            news_rows.append([r.get(c, "") for c in news_cols])
    news_table = table_html(news_cols, news_rows) if news_rows else '<p class="empty">뉴스 데이터 없음</p>'

    html_doc = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>실전매매 클린 브리핑 {date_key}</title>
<style>
:root{{--bg:#f4f6fb;--card:#fff;--text:#111827;--muted:#64748b;--line:#e5e7eb}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans KR",Arial,sans-serif;line-height:1.55}}
header{{background:linear-gradient(135deg,#0f172a,#1e40af);color:white;padding:30px 20px 38px;border-radius:0 0 28px 28px}}header h1{{margin:0 0 8px;font-size:30px}}header p{{margin:0;color:#dbeafe}}
.wrap{{max-width:1180px;margin:-24px auto 42px;padding:0 16px}}.kpis{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-bottom:14px}}
.kpi,.panel,.stock-card{{background:#fff;border:1px solid var(--line);border-radius:22px;box-shadow:0 10px 28px rgba(15,23,42,.08)}}.kpi{{padding:16px}}.kpi label{{display:block;font-size:13px;color:var(--muted);margin-bottom:6px}}.kpi strong{{font-size:20px}}
.tabs{{display:flex;gap:8px;overflow-x:auto;padding:8px 0 14px;position:sticky;top:0;background:var(--bg);z-index:5}}.tabs a{{white-space:nowrap;text-decoration:none;color:#1e3a8a;background:#e0e7ff;padding:10px 13px;border-radius:999px;font-weight:800;font-size:13px}}
.panel{{padding:18px;margin:14px 0}}.stock-card{{padding:18px;margin:14px 0}}.stock-head{{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;border-bottom:1px solid var(--line);padding-bottom:12px}}.stock-head h2{{display:inline;margin:0;font-size:22px}}.sub{{margin:6px 0 0;color:#64748b;font-weight:700}}
.rank{{display:inline-flex;align-items:center;justify-content:center;min-width:42px;height:34px;border-radius:12px;background:#eef2ff;color:#3730a3;font-weight:900;margin-right:10px;padding:0 8px}}.badge{{padding:8px 12px;border-radius:999px;font-size:13px;font-weight:900;white-space:nowrap}}.badge.good{{background:#dcfce7;color:#166534}}.badge.warn{{background:#fef3c7;color:#92400e}}
.metric-grid,.mini-grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:16px 0}}.mini-grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}.metric-grid div,.mini-grid p{{background:#f8fafc;border-radius:14px;padding:12px;margin:0}}.metric-grid label,.mini-grid label{{display:block;color:#64748b;font-size:12px;margin-bottom:6px}}
.guide{{background:#f8fafc;border-left:4px solid #93c5fd;border-radius:12px;padding:12px;margin:12px 0 0;color:#334155}}.table-wrap{{overflow:auto;border:1px solid var(--line);border-radius:16px}}.data-table{{border-collapse:collapse;width:100%;font-size:13px;background:white}}.data-table th{{background:#f1f5f9;text-align:left;color:#334155;position:sticky;top:0}}.data-table th,.data-table td{{padding:10px;border-bottom:1px solid #eef2f7;vertical-align:top}}
.chips{{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}}.chip{{display:inline-block;background:#f1f5f9;border:1px solid #e2e8f0;padding:8px 11px;border-radius:999px;font-weight:700;color:#334155}}.empty{{background:#f8fafc;border:1px dashed #cbd5e1;border-radius:16px;padding:20px;color:#64748b}}.note{{color:#64748b;font-size:13px;margin-top:8px}}footer{{text-align:center;color:#64748b;font-size:12px;padding:30px 10px 40px}}
@media(max-width:760px){{.kpis,.metric-grid,.mini-grid{{grid-template-columns:1fr}}.stock-head{{flex-direction:column}}}}
</style>
</head>
<body>
<header><h1>실전매매 클린 브리핑</h1><p>{date_key} · HTML 정리본 · 투자 판단 보조용</p></header>
<main class="wrap">
  <section class="kpis">
    <div class="kpi"><label>시장모드</label><strong>{esc(market_mode)}</strong></div>
    <div class="kpi"><label>분석 후보</label><strong>{esc(candidate_count)}개</strong></div>
    <div class="kpi"><label>상위 후보</label><strong>{esc(top_name)}</strong></div>
    <div class="kpi"><label>과열 후보</label><strong>{esc(hot_count)}개</strong></div>
  </section>
  <nav class="tabs"><a href="#briefing">시장브리핑</a><a href="#candidates">신규 후보 TOP</a><a href="#continuous">연속추천</a><a href="#backtest">백테스트 요약</a><a href="#news">뉴스</a></nav>
  <section id="briefing" class="panel"><h2>오늘 시장브리핑</h2>{brief_table}<h3>상위 섹터 흐름</h3><div class="chips">{sector_html}</div></section>
  <section id="candidates" class="panel"><h2>신규 후보 TOP</h2><p class="note">엑셀의 TOP후보_요약 시트를 기준으로 핵심 정보만 카드형으로 정리했습니다.</p></section>
  {''.join(cards)}
  <section id="continuous" class="panel"><h2>연속추천 관찰</h2><p class="note">며칠째 반복 등장하는 종목은 단발성 후보보다 우선 관찰합니다. 첫 실행일은 모두 신규/단발 후보로 표시될 수 있습니다.</p>{cont_table}</section>
  <section id="backtest" class="panel"><h2>백테스트 실험실 요약</h2><p class="note">난잡한 계산영역 대신 종목별 대표 행만 요약했습니다. 세부 계산은 엑셀의 실험실_요약/백테스트_실험실 시트에서 확인하세요.</p>{lab_table}</section>
  <section id="news" class="panel"><h2>뉴스 이슈</h2>{news_table}</section>
</main>
<footer>본 리포트는 투자 판단 보조용이며 매수·매도 권유가 아닙니다. 실제 매매 전 공시·뉴스·호가·손실한도를 확인하세요.</footer>
</body></html>"""

    return html_doc


def main() -> int:
    try:
        xlsx_path = Path(sys.argv[1]) if len(sys.argv) >= 2 else find_latest_xlsx()
        html_doc = build_html(xlsx_path)

        m = re.search(r"(20\d{6})", xlsx_path.name)
        date_key = m.group(1) if m else datetime.now().strftime("%Y%m%d")

        out_paths = [
            Path("docs/index.html"),
            Path("docs/reports") / date_key / "index.html",
        ]

        for out in out_paths:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(html_doc, encoding="utf-8")

        bad_markers = ["dtype: object", "Name:", ">NaN"]
        bad_found = [m for m in bad_markers if m in html_doc]
        if bad_found:
            print(f"⚠️ HTML 정리 경고: 남아있는 난잡한 표시 {bad_found}")
        else:
            print(f"✅ 클린 HTML 브리핑 재생성 완료: {', '.join(str(p) for p in out_paths)}")

        return 0
    except Exception as e:
        print(f"❌ 클린 HTML 브리핑 재생성 실패: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
