#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone, timedelta
import csv
import html
import re
import shutil
import pandas as pd

KST = timezone(timedelta(hours=9))

SHEET_MAP = {
    "모바일_대시보드": "legacy_mobile_dashboard",
    "TOP후보_요약": "legacy_top_candidates",
    "추천 리스트": "legacy_full_recommendations",
    "진입시나리오": "legacy_entry_scenario",
    "진입가이드_요약": "legacy_entry_guide",
    "연속추천_관찰": "legacy_continuous",
    "종목카드_TOP15": "legacy_stock_cards_top15",
    "추천성과_검증": "legacy_recommendation_performance",
    "전략백테스트요약": "legacy_strategy_backtest_summary",
    "계좌백테스트요약": "legacy_account_backtest_summary",
    "백테스트검증가이드": "legacy_backtest_validation_guide",
    "보유종목_판단": "legacy_holding_decision",
    "시장상태": "legacy_market_state",
}

def now():
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")

def esc(x):
    return html.escape(str(x if x is not None else ""))

def clean_value(x):
    if x is None:
        return ""
    if isinstance(x, float) and pd.isna(x):
        return ""
    s = str(x).strip()
    if s.lower() in {"nan", "none", "nat"}:
        return ""
    return s

def safe_int(x, default=999999):
    s = clean_value(x).replace(",", "")
    try:
        return int(float(s))
    except Exception:
        return default

def find_latest_xlsx() -> Path | None:
    roots = [Path("."), Path("stock_report"), Path("docs")]
    files = []
    seen = set()
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*.xlsx"):
            if not p.is_file():
                continue
            path_text = p.as_posix()
            if "docs/downloads" in path_text:
                continue
            if "__MACOSX" in path_text:
                continue
            key = p.resolve()
            if key in seen:
                continue
            seen.add(key)
            files.append(p)
    if not files:
        return None
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0]

def normalize_columns(cols):
    out = []
    seen = {}
    for c in cols:
        name = clean_value(c)
        if not name:
            name = "컬럼"
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 1
        out.append(name)
    return out

def read_sheet_table(xlsx: Path, sheet_name: str) -> pd.DataFrame:
    try:
        raw = pd.read_excel(xlsx, sheet_name=sheet_name, header=None, dtype=object)
    except Exception:
        return pd.DataFrame()

    if raw.empty:
        return pd.DataFrame()

    header_row = None
    keywords = {
        "순위", "종목명", "stock_name", "시장", "섹터/분야", "후보출처",
        "현재가", "점수", "진입판정", "주목등급", "TP전략", "SL전략",
        "recommend_date", "rank", "status", "stock_name", "entry_guide",
        "백테스트시작일", "구분", "판단", "항목"
    }

    for idx in range(min(len(raw), 20)):
        values = [clean_value(v) for v in raw.iloc[idx].tolist()]
        non_empty = [v for v in values if v]
        if len(non_empty) < 2:
            continue
        score = sum(1 for v in non_empty if v in keywords or any(k in v for k in ["종목", "순위", "전략", "수익", "진입", "손절", "익절"]))
        if score >= 2:
            header_row = idx
            break

    if header_row is None:
        header_row = 0

    header = normalize_columns(raw.iloc[header_row].tolist())
    df = raw.iloc[header_row + 1:].copy()
    df.columns = header
    df = df.dropna(how="all")
    df = df.applymap(clean_value)

    empty_cols = [c for c in df.columns if not c or str(c).startswith("Unnamed")]
    df = df.drop(columns=empty_cols, errors="ignore")
    return df

def write_df(df: pd.DataFrame, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")

def read_csv_rows(path: Path, limit=999):
    if not path.exists():
        return []
    for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
        try:
            with path.open(encoding=enc, newline="") as f:
                return list(csv.DictReader(f))[:limit]
        except Exception:
            pass
    return []

def pick(row, names):
    if not row:
        return ""
    lower = {str(k).strip().lower(): k for k in row.keys()}
    for name in names:
        k = lower.get(name.lower())
        if k and clean_value(row.get(k)):
            return clean_value(row.get(k))
    for k, v in row.items():
        kk = str(k).lower()
        for name in names:
            if name.lower() in kk and clean_value(v):
                return clean_value(v)
    return ""

def table_html(rows, headers=None, max_rows=40):
    rows = rows[:max_rows]
    if not headers:
        headers = []
        for r in rows:
            for k in r.keys():
                if k not in headers:
                    headers.append(k)
    if not rows:
        return "<p class='hint'>표시할 데이터가 없습니다.</p>"
    th = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = ""
    for r in rows:
        body += "<tr>" + "".join(f"<td>{esc(r.get(h,''))}</td>" for h in headers) + "</tr>"
    return f"<div class='tablewrap'><table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>"

CSS = """
body{margin:0;background:#f6f7fb;color:#111827;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.wrap{max-width:1080px;margin:auto;padding:20px}
.hero{background:#172554;color:white;border-radius:22px;padding:22px;margin-bottom:16px}
.hero p{color:#dbeafe;line-height:1.55}
.box,.card{background:white;border-radius:18px;padding:16px;margin-bottom:16px;box-shadow:0 4px 16px rgba(0,0,0,.06)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}
.card h3{margin:0 0 8px}.pill{display:inline-block;background:#dbeafe;color:#1e40af;border-radius:999px;padding:5px 10px;font-size:12px;font-weight:700}
.meta,.hint{font-size:13px;color:#6b7280;line-height:1.55}
p,li{font-size:14px;line-height:1.68;color:#374151}
.tablewrap{overflow:auto;background:white;border-radius:16px;border:1px solid #e5e7eb}
table{border-collapse:collapse;width:100%;min-width:900px}
th,td{border-bottom:1px solid #e5e7eb;padding:10px;font-size:13px;text-align:left;vertical-align:top}
th{background:#f3f4f6;color:#334155}
a{color:#2563eb;font-weight:700;text-decoration:none}
.links{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px}
.links a{display:block;background:#fff;border-radius:16px;padding:14px;box-shadow:0 4px 16px rgba(0,0,0,.06)}
"""

def write_page(path: Path, title: str, subtitle: str, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"""<!doctype html>
<html lang="ko">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title><style>{CSS}</style></head>
<body><main class="wrap"><section class="hero"><h1>{esc(title)}</h1><p>{esc(subtitle)}</p></section>{content}</main></body></html>
""", encoding="utf-8")

def build_top_cards(rows):
    cards = ""
    for r in rows[:15]:
        rank = pick(r, ["순위", "rank"]) or ""
        name = pick(r, ["종목명", "stock_name"])
        sector = pick(r, ["섹터/분야", "분야", "sector"])
        score = pick(r, ["실전점수", "점수", "score", "기본점수"])
        price = pick(r, ["현재가", "current_price"])
        entry = pick(r, ["진입판정", "entry_action", "entry_guide"])
        tp = pick(r, ["익절계획", "take_profit_guide"])
        sl = pick(r, ["손절계획", "stop_loss_guide"])
        trend = pick(r, ["추세", "백테스트신뢰도"])
        cards += f"""<article class="card">
<h3>#{esc(rank)} {esc(name)}</h3>
<div class="meta">{esc(sector)} · 현재가 {esc(price)} · 점수 {esc(score)}</div>
<p><span class="pill">{esc(entry or '진입판정 확인')}</span></p>
<p><b>익절:</b> {esc(tp)}<br><b>손절:</b> {esc(sl)}<br><b>추세/검증:</b> {esc(trend)}</p>
</article>"""
    return f"<section class='grid'>{cards}</section>" if cards else "<p class='hint'>TOP 후보 데이터가 없습니다.</p>"

def build_entry_cards(entry_rows, guide_rows):
    guide_by_name = {pick(r, ["stock_name", "종목명"]): r for r in guide_rows}
    cards = ""
    for r in entry_rows[:15]:
        name = pick(r, ["종목명", "stock_name"])
        g = guide_by_name.get(name, {})
        cards += f"""<article class="card">
<h3>{esc(pick(r, ['순위','rank']))}. {esc(name)}</h3>
<div class="meta">{esc(pick(r, ['섹터/분야','sector']))} · 현재가 {esc(pick(r, ['현재가','current_price']))}</div>
<p><b>공격/기준/보수:</b> {esc(pick(r, ['공격진입가']))} / {esc(pick(r, ['기준진입가']))} / {esc(pick(r, ['보수진입가']))}</p>
<p><b>돌파/손절:</b> {esc(pick(r, ['돌파진입가']))} / {esc(pick(r, ['손절기준가']))}</p>
<p><b>가이드:</b> {esc(pick(g, ['entry_guide']))}</p>
<p><b>추격금지:</b> {esc(pick(g, ['do_not_chase']))}</p>
</article>"""
    return f"<section class='grid'>{cards}</section>" if cards else "<p class='hint'>진입 시나리오 데이터가 없습니다.</p>"

def build_strategy_summary(strategy_rows, perf_rows, account_rows, guide_rows):
    parts = []
    if account_rows:
        parts.append("<section class='box'><h2>계좌 백테스트 요약</h2>" + table_html(account_rows, max_rows=5) + "</section>")
    if guide_rows:
        parts.append("<section class='box'><h2>백테스트 검증 가이드</h2>" + table_html(guide_rows, max_rows=12) + "</section>")
    if perf_rows:
        headers = ["recommend_date","session","rank","stock_name","sector","score","recommend_price","latest_price","latest_return_pct","max_observed_return_pct"]
        parts.append("<section class='box'><h2>추천성과 검증</h2>" + table_html(perf_rows, headers=[h for h in headers if h in perf_rows[0]], max_rows=30) + "</section>")
    if strategy_rows:
        headers = ["종목명","종목코드","TP전략","SL전략","수익률","MDD","승률","거래횟수","백테스트신뢰도"]
        parts.append("<section class='box'><h2>전략 백테스트 요약</h2>" + table_html(strategy_rows, headers=[h for h in headers if h in strategy_rows[0]], max_rows=40) + "</section>")
    return "".join(parts) or "<p class='hint'>전략 검증 데이터가 없습니다.</p>"

def build_outputs():
    data = Path("docs/data")
    details = Path("docs/details")
    data.mkdir(parents=True, exist_ok=True)
    details.mkdir(parents=True, exist_ok=True)

    xlsx = find_latest_xlsx()
    status_rows = [{"key": "checked_at", "value": now()}]

    if not xlsx:
        status_rows.append({"key": "xlsx", "value": "not_found"})
        write_df(pd.DataFrame(status_rows), data / "latest_legacy_sections_status.csv")
        print("⚠️ legacy restore: xlsx not found")
        return

    status_rows.append({"key": "xlsx", "value": xlsx.as_posix()})
    extracted = {}

    for sheet, slug in SHEET_MAP.items():
        df = read_sheet_table(xlsx, sheet)
        if df.empty:
            status_rows.append({"key": f"sheet_{sheet}", "value": "missing_or_empty"})
            continue
        out = data / f"latest_{slug}.csv"
        write_df(df, out)
        extracted[slug] = df.to_dict("records")
        status_rows.append({"key": f"sheet_{sheet}", "value": f"ok:{len(df)}"})

    # legacy-compatible aliases for existing app pages/data
    top_rows = extracted.get("legacy_top_candidates", [])
    mobile_rows = extracted.get("legacy_mobile_dashboard", [])
    full_rows = extracted.get("legacy_full_recommendations", [])
    entry_rows = extracted.get("legacy_entry_scenario", [])
    guide_rows = extracted.get("legacy_entry_guide", [])
    continuous_rows = extracted.get("legacy_continuous", [])
    perf_rows = extracted.get("legacy_recommendation_performance", [])
    strategy_rows = extracted.get("legacy_strategy_backtest_summary", [])
    account_rows = extracted.get("legacy_account_backtest_summary", [])
    validation_rows = extracted.get("legacy_backtest_validation_guide", [])
    holding_decision_rows = extracted.get("legacy_holding_decision", [])

    if top_rows:
        alias = []
        guide_by_name = {pick(r, ["stock_name","종목명"]): r for r in guide_rows}
        for r in top_rows:
            name = pick(r, ["종목명","stock_name"])
            g = guide_by_name.get(name, {})
            alias.append({
                "rank": pick(r, ["순위"]),
                "stock_name": name,
                "stock_code": pick(r, ["종목코드","stock_code"]),
                "market": pick(r, ["시장"]),
                "sector": pick(r, ["섹터/분야","분야"]),
                "source": pick(r, ["후보출처"]),
                "current_price": pick(r, ["현재가"]),
                "base_score": pick(r, ["기본점수"]),
                "score": pick(r, ["실전점수","점수"]),
                "overheat": pick(r, ["과열판정"]),
                "entry_decision": pick(r, ["진입판정"]),
                "backtest_confidence": pick(r, ["백테스트신뢰도"]),
                "take_profit_plan": pick(r, ["익절계획"]) or pick(g, ["take_profit_guide"]),
                "stop_loss_plan": pick(r, ["손절계획"]) or pick(g, ["stop_loss_guide"]),
                "trend": pick(r, ["추세"]),
                "entry_guide": pick(g, ["entry_guide"]),
                "do_not_chase": pick(g, ["do_not_chase"]),
                "check_points": pick(g, ["check_points"]),
                "stock_description": f"{name}은(는) 기존 엑셀 리포트의 {pick(r, ['섹터/분야','분야']) or '분야 미확인'} 후보입니다. 후보출처는 {pick(r, ['후보출처']) or '확인 필요'}이며, 실전점수·진입판정·익절/손절계획은 엑셀 계산값을 그대로 사용합니다.",
            })
        write_df(pd.DataFrame(alias), data / "latest_recommendation_top15_full.csv")
        write_df(pd.DataFrame(alias), data / "latest_recommendation_analysis.csv")

    # Pages built from legacy excel sheets
    write_page(
        details / "legacy_top15.html",
        "추천 TOP15 · 기존 엑셀 데이터",
        f"원천 파일: {xlsx.as_posix()} · TOP후보_요약/진입가이드_요약 시트를 그대로 활용합니다.",
        build_top_cards(top_rows) + "<section class='box'><h2>TOP 후보 요약표</h2>" + table_html(top_rows, max_rows=20) + "</section>"
    )

    write_page(
        details / "legacy_full_recommendations.html",
        "전체 추천 명단 · 기존 엑셀 데이터",
        f"원천 파일: {xlsx.as_posix()} · 추천 리스트 시트를 그대로 활용합니다.",
        table_html(full_rows, max_rows=80)
    )

    write_page(
        details / "legacy_entry_scenario.html",
        "진입 시나리오 · 기존 엑셀 데이터",
        f"원천 파일: {xlsx.as_posix()} · 진입시나리오/진입가이드_요약 시트를 그대로 활용합니다.",
        build_entry_cards(entry_rows, guide_rows) + "<section class='box'><h2>진입가이드 요약표</h2>" + table_html(guide_rows, max_rows=20) + "</section>"
    )

    write_page(
        details / "legacy_continuous.html",
        "연속추천 관찰 · 기존 엑셀 데이터",
        f"원천 파일: {xlsx.as_posix()} · 연속추천_관찰 시트를 그대로 활용합니다.",
        table_html(continuous_rows, max_rows=40)
    )

    write_page(
        details / "legacy_strategy_validation.html",
        "전략 추천/검증 · 기존 엑셀 데이터",
        f"원천 파일: {xlsx.as_posix()} · 전략백테스트요약/추천성과_검증/계좌백테스트요약 시트를 활용합니다.",
        build_strategy_summary(strategy_rows, perf_rows, account_rows, validation_rows)
    )

    write_page(
        details / "legacy_mobile_dashboard.html",
        "모바일 대시보드 원본 · 기존 엑셀 데이터",
        f"원천 파일: {xlsx.as_posix()} · 모바일_대시보드 시트를 그대로 활용합니다.",
        table_html(mobile_rows, max_rows=20)
    )

    # Overwrite familiar URLs with legacy-backed pages too.
    shutil.copyfile(details / "legacy_top15.html", details / "recommendation_top15.html")
    shutil.copyfile(details / "legacy_full_recommendations.html", details / "recommendation_full_list.html")
    shutil.copyfile(details / "legacy_entry_scenario.html", details / "entry_scenario.html")
    shutil.copyfile(details / "legacy_continuous.html", details / "continuous.html")

    if holding_decision_rows:
        write_page(
            details / "legacy_holding_decision.html",
            "보유종목 판단 · 기존 엑셀 데이터",
            f"원천 파일: {xlsx.as_posix()} · 보유종목_판단 시트를 활용합니다.",
            table_html(holding_decision_rows, max_rows=40)
        )

    write_df(pd.DataFrame(status_rows), data / "latest_legacy_sections_status.csv")
    print("✅ legacy Excel sections restored")
    print(f"xlsx: {xlsx}")
    print(f"sheets: {len(extracted)}")

if __name__ == "__main__":
    build_outputs()
