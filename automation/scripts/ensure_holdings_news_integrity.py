#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone, timedelta
import html
import os
import re
import pandas as pd

KST = timezone(timedelta(hours=9))


def now_kst() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")


def read_csv_safely(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
        try:
            return pd.read_csv(path, dtype=str, encoding=enc).fillna("")
        except Exception:
            pass
    try:
        return pd.read_csv(path, dtype=str).fillna("")
    except Exception:
        return pd.DataFrame()


def write_csv_safely(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.fillna("").to_csv(path, index=False, encoding="utf-8-sig")


def norm_text(x) -> str:
    if x is None:
        return ""
    s = str(x).strip()
    if s.lower() in {"nan", "none", "null"}:
        return ""
    return s


def normalize_code(code) -> str:
    s = norm_text(code)
    if not s:
        return ""
    s = s.replace("=", "").replace('"', "").replace("'", "").strip()
    s = s.replace(",", "").replace(" ", "")
    if re.fullmatch(r"\d+\.0", s):
        s = s[:-2]
    if re.fullmatch(r"\d+", s):
        return s.zfill(6)
    return s.upper()


def to_float(x):
    s = norm_text(x)
    if not s:
        return None
    s = re.sub(r"[^\d\.\-]", "", s)
    if not s or s in {"-", ".", "-."}:
        return None
    try:
        return float(s)
    except Exception:
        return None


def find_col(df: pd.DataFrame, names: list[str]) -> str | None:
    if df.empty:
        return None
    lower_map = {str(c).strip().lower(): c for c in df.columns}
    for n in names:
        key = n.strip().lower()
        if key in lower_map:
            return lower_map[key]
    for c in df.columns:
        cc = str(c).strip().lower()
        for n in names:
            if n.strip().lower() in cc:
                return c
    return None


def normalize_holdings_df(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["status","stock_name","stock_code","quantity","avg_price","buy_date","strategy","target_price","stop_loss","weight_note","memo"]
    if df.empty:
        return pd.DataFrame(columns=cols)

    mapping = {
        "status": ["status", "상태"],
        "stock_name": ["stock_name", "종목명", "name"],
        "stock_code": ["stock_code", "종목코드", "code", "ticker"],
        "quantity": ["quantity", "보유수량", "수량", "qty"],
        "avg_price": ["avg_price", "평균단가", "매입단가", "평단가"],
        "buy_date": ["buy_date", "매수일", "매입일"],
        "strategy": ["strategy", "전략구분", "전략"],
        "target_price": ["target_price", "목표가"],
        "stop_loss": ["stop_loss", "손절가"],
        "weight_note": ["weight_note", "비중메모"],
        "memo": ["memo", "메모"],
    }
    out = pd.DataFrame()
    for target, names in mapping.items():
        col = find_col(df, names)
        out[target] = df[col].map(norm_text) if col else ""
    out["stock_code"] = out["stock_code"].map(normalize_code)
    out["stock_name"] = out["stock_name"].map(norm_text)
    out = out[(out["stock_name"] != "") | (out["stock_code"] != "")].copy()
    return out[cols]


def build_code_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for path in [Path("종목분야_수동입력.csv"), Path("TOSS_수동후보.csv"), Path("holdings_manual_input.csv"), Path("trade_log_manual_input.csv")]:
        df = read_csv_safely(path)
        if df.empty:
            continue
        name_col = find_col(df, ["stock_name", "종목명", "name"])
        code_col = find_col(df, ["stock_code", "종목코드", "code", "ticker"])
        if not name_col or not code_col:
            continue
        for _, row in df.iterrows():
            name = norm_text(row.get(name_col))
            code = normalize_code(row.get(code_col))
            if name and code:
                lookup[name] = code

    for xlsx in sorted(Path(".").glob("*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)[:4]:
        try:
            sheets = pd.read_excel(xlsx, sheet_name=None, dtype=str)
        except Exception:
            continue
        for df in sheets.values():
            if df.empty:
                continue
            name_col = find_col(df, ["stock_name", "종목명", "name"])
            code_col = find_col(df, ["stock_code", "종목코드", "code", "ticker"])
            if not name_col or not code_col:
                continue
            for _, row in df.iterrows():
                name = norm_text(row.get(name_col))
                code = normalize_code(row.get(code_col))
                if name and code:
                    lookup.setdefault(name, code)
    return lookup


def build_price_lookup() -> tuple[dict[str, float], dict[str, float]]:
    by_code: dict[str, float] = {}
    by_name: dict[str, float] = {}
    frames = []

    data_dir = Path("docs/data")
    if data_dir.exists():
        for csv in data_dir.glob("*.csv"):
            df = read_csv_safely(csv)
            if not df.empty:
                frames.append(df)

    for xlsx in sorted(Path(".").glob("*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)[:5]:
        try:
            sheets = pd.read_excel(xlsx, sheet_name=None, dtype=str)
            frames.extend(sheets.values())
        except Exception:
            continue

    price_cols = ["current_price", "현재가", "기준가", "추천가", "종가", "close", "price", "last_price"]
    for df in frames:
        if df.empty:
            continue
        name_col = find_col(df, ["stock_name", "종목명", "name"])
        code_col = find_col(df, ["stock_code", "종목코드", "code", "ticker"])
        price_col = find_col(df, price_cols)
        if not price_col:
            continue
        for _, row in df.iterrows():
            price = to_float(row.get(price_col))
            if price is None or price <= 0:
                continue
            if code_col:
                code = normalize_code(row.get(code_col))
                if code:
                    by_code.setdefault(code, price)
            if name_col:
                name = norm_text(row.get(name_col))
                if name:
                    by_name.setdefault(name, price)
    return by_code, by_name


def make_decision(pnl_pct, target, stop, current):
    if current is None:
        return "PRICE_NOT_MATCHED", "현재가 매칭 필요. stock_code 6자리/종목명 확인 후 다음 실행에서 재검증."
    if stop and current <= stop:
        return "STOP_WATCH", "손절 기준가 근접 또는 이탈. 추가매수보다 리스크 축소 우선."
    if target and current >= target:
        return "TAKE_PROFIT", "목표가 도달 또는 근접. 일부 익절/분할매도 검토."
    if pnl_pct is not None:
        if pnl_pct >= 8:
            return "TAKE_PROFIT_1", "습관형 1차 익절권. 일부 익절 후 잔량 관리 검토."
        if pnl_pct <= -7:
            return "STOP_WATCH", "습관형 손절권. 물타기 금지, 손실 확대 방지 우선."
    return "HOLD", "보유 유지. 뉴스·거래량·추천 재등장 여부 확인."


def ensure_holdings_exports():
    eng = normalize_holdings_df(read_csv_safely(Path("holdings_manual_input.csv")))
    kor = normalize_holdings_df(read_csv_safely(Path("보유종목_수동입력.csv")))
    holdings = eng if not eng.empty else kor
    source_file = "holdings_manual_input.csv" if not eng.empty else ("보유종목_수동입력.csv" if not kor.empty else "not_found")

    if holdings.empty:
        diag = pd.DataFrame([{
            "status": "NO_HOLDINGS_INPUT",
            "message": "holdings_manual_input.csv 파일이 비어 있거나 루트에 없습니다.",
            "checked_at": now_kst(),
        }])
        for p in ["latest_holdings.csv", "latest_holding_deep_analysis.csv", "latest_holding_action_guide.csv"]:
            write_csv_safely(diag, Path("docs/data") / p)
        return

    code_lookup = build_code_lookup()
    price_by_code, price_by_name = build_price_lookup()
    holdings["stock_code"] = holdings.apply(lambda r: normalize_code(r["stock_code"]) or code_lookup.get(norm_text(r["stock_name"]), ""), axis=1)

    deep_rows = []
    action_rows = []
    for _, r in holdings.iterrows():
        name = norm_text(r.get("stock_name"))
        code = normalize_code(r.get("stock_code"))
        qty = to_float(r.get("quantity"))
        avg = to_float(r.get("avg_price"))
        target = to_float(r.get("target_price"))
        stop = to_float(r.get("stop_loss"))

        current = None
        source = "not_matched"
        if code and code in price_by_code:
            current = price_by_code[code]
            source = "matched_by_code"
        elif name and name in price_by_name:
            current = price_by_name[name]
            source = "matched_by_name"
        elif avg:
            current = avg
            source = "fallback_avg_price"

        pnl = None
        if current and avg and avg > 0:
            pnl = (current / avg - 1) * 100

        auto_tp1 = round(avg * 1.08, 2) if avg else ""
        auto_tp2 = round(avg * 1.15, 2) if avg else ""
        auto_sl = round(avg * 0.93, 2) if avg else ""
        decision, memo = make_decision(pnl, target, stop, current)

        deep_rows.append({
            "source_file": source_file,
            "status": r.get("status", ""),
            "stock_name": name,
            "stock_code": code,
            "quantity": qty if qty is not None else "",
            "avg_price": avg if avg is not None else "",
            "current_price": current if current is not None else "",
            "current_price_source": source,
            "unrealized_pnl_pct": round(pnl, 2) if pnl is not None else "",
            "target_price": target if target is not None else "",
            "stop_loss": stop if stop is not None else "",
            "decision": decision,
            "memo": memo,
            "checked_at": now_kst(),
        })
        action_rows.append({
            "stock_name": name,
            "stock_code": code,
            "decision": decision,
            "entry_or_add_guide": "추가매수는 손절가 아래 금지. 재추천/거래량 증가/지지 확인 시만 분할 접근.",
            "take_profit_1": target if target else auto_tp1,
            "take_profit_2": auto_tp2,
            "stop_loss": stop if stop else auto_sl,
            "sell_guide": memo,
            "price_match_status": source,
        })

    deep = pd.DataFrame(deep_rows)
    actions = pd.DataFrame(action_rows)
    write_csv_safely(holdings, Path("docs/data/latest_holdings.csv"))
    write_csv_safely(deep, Path("docs/data/latest_holding_deep_analysis.csv"))
    write_csv_safely(actions, Path("docs/data/latest_holding_action_guide.csv"))

    trs = "".join(
        f"<tr><td>{html.escape(str(r['stock_name']))}</td><td>{html.escape(str(r['stock_code']))}</td><td>{html.escape(str(r['decision']))}</td><td>{html.escape(str(r['avg_price']))}</td><td>{html.escape(str(r['current_price']))}</td><td>{html.escape(str(r['unrealized_pnl_pct']))}</td><td>{html.escape(str(r['current_price_source']))}</td><td>{html.escape(str(r['memo']))}</td></tr>"
        for r in deep_rows
    )
    page = Path("docs/v11_holdings/index.html")
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>v11 보유종목 심화분석</title><style>body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f6f7fb;color:#111827;margin:0}}.wrap{{max-width:1100px;margin:0 auto;padding:20px}}.hero{{background:#111827;color:white;border-radius:20px;padding:20px;margin-bottom:16px}}.tablebox{{overflow:auto;background:white;border-radius:16px;box-shadow:0 4px 16px rgba(0,0,0,.06)}}table{{border-collapse:collapse;width:100%;min-width:900px}}th,td{{border-bottom:1px solid #e5e7eb;padding:10px;text-align:left;font-size:13px;vertical-align:top}}th{{background:#f3f4f6}}.note{{color:#6b7280;font-size:13px;line-height:1.6}}</style></head><body><main class="wrap"><section class="hero"><h1>v11 보유종목 심화분석</h1><p>갱신: {html.escape(now_kst())}</p><p>입력 파일: {html.escape(source_file)} / 보유종목 {len(deep_rows)}개</p></section><p class="note">current_price_source가 fallback_avg_price이면 현재가를 찾지 못해 평균단가 기준으로 임시 계산한 상태입니다.</p><div class="tablebox"><table><thead><tr><th>종목명</th><th>코드</th><th>판단</th><th>평균단가</th><th>현재가</th><th>손익률%</th><th>매칭상태</th><th>메모</th></tr></thead><tbody>{trs}</tbody></table></div></main></body></html>""", encoding="utf-8")


def ensure_naver_detail_exports():
    data_dir = Path("docs/data")
    data_dir.mkdir(parents=True, exist_ok=True)
    detail_path = data_dir / "latest_news_detail.csv"
    detail = read_csv_safely(detail_path)

    if detail.empty:
        for xlsx in sorted(Path(".").glob("*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)[:5]:
            try:
                sheets = pd.read_excel(xlsx, sheet_name=None, dtype=str)
            except Exception:
                continue
            for sname, df in sheets.items():
                if "뉴스" in str(sname) and ("상세" in str(sname) or "detail" in str(sname).lower()):
                    detail = df.fillna("")
                    break
            if not detail.empty:
                break

    api_state = "configured" if os.environ.get("NAVER_CLIENT_ID") and os.environ.get("NAVER_CLIENT_SECRET") else "missing_or_not_passed"

    if detail.empty:
        detail = pd.DataFrame([{
            "category": "diagnostic",
            "query": "",
            "title": "네이버뉴스 상세 데이터가 생성되지 않았습니다.",
            "description": "NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 설정 또는 add_naver_news_summary.py 실행 로그를 확인하세요.",
            "link": "",
            "pubDate": "",
            "api_state": api_state,
            "checked_at": now_kst(),
        }])
    else:
        detail["api_state"] = api_state
        detail["checked_at"] = now_kst()

    write_csv_safely(detail, detail_path)

    cards = ""
    for _, row in detail.head(200).iterrows():
        title = norm_text(row.get("title")) or norm_text(row.get("제목")) or "제목 없음"
        desc = norm_text(row.get("description")) or norm_text(row.get("요약")) or norm_text(row.get("본문")) or ""
        link = norm_text(row.get("link")) or norm_text(row.get("링크")) or ""
        category = norm_text(row.get("category")) or norm_text(row.get("구분")) or ""
        query = norm_text(row.get("query")) or norm_text(row.get("검색어")) or ""
        link_html = f'<a href="{html.escape(link)}" target="_blank" rel="noopener">기사 열기</a>' if link else '<span>링크 없음</span>'
        cards += f"<article class='card'><div class='meta'>{html.escape(category)} {html.escape(query)}</div><h2>{html.escape(title)}</h2><p>{html.escape(desc)}</p><div>{link_html}</div></article>"

    page = Path("docs/details/naver_news.html")
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>네이버뉴스 상세</title><style>body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f6f7fb;color:#111827;margin:0}}.wrap{{max-width:900px;margin:0 auto;padding:20px}}.hero{{background:#064e3b;color:white;border-radius:20px;padding:20px;margin-bottom:16px}}.card{{background:white;border-radius:16px;padding:16px;margin-bottom:12px;box-shadow:0 4px 16px rgba(0,0,0,.06)}}.card h2{{font-size:17px;margin:6px 0 8px}}.card p{{font-size:14px;line-height:1.55;color:#374151}}.meta{{font-size:12px;color:#059669}}a{{color:#2563eb;font-weight:700}}</style></head><body><main class="wrap"><section class="hero"><h1>네이버뉴스 상세</h1><p>갱신: {html.escape(now_kst())}</p><p>API 상태: {html.escape(api_state)}</p></section>{cards}</main></body></html>""", encoding="utf-8")


def main() -> int:
    ensure_holdings_exports()
    ensure_naver_detail_exports()
    print("✅ holdings code/current-price matching exports ensured")
    print("✅ naver news detail exports ensured")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
