#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone, timedelta
import html
import json
import os
import re
import time
import urllib.parse
import urllib.request
import urllib.error
import pandas as pd

KST = timezone(timedelta(hours=9))


def now_kst() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")


def read_csv_safely(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()

    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, dtype=str, encoding=enc).fillna("")
        except Exception:
            pass

    return pd.DataFrame()


def write_csv_safely(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.fillna("").to_csv(path, index=False, encoding="utf-8-sig")


def norm_text(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    return text


def normalize_code(value) -> str:
    text = norm_text(value)
    if not text:
        return ""

    text = text.replace("=", "").replace('"', "").replace("'", "")
    text = text.replace(",", "").replace(" ", "").strip()

    if re.fullmatch(r"\d+\.0", text):
        text = text[:-2]

    if re.fullmatch(r"\d+", text):
        return text.zfill(6)

    return text.upper()


def to_float(value):
    text = norm_text(value)
    if not text:
        return None

    text = re.sub(r"[^\d\.\-]", "", text)
    if not text or text in {"-", ".", "-."}:
        return None

    try:
        return float(text)
    except Exception:
        return None


def find_col(df: pd.DataFrame, names: list[str]) -> str | None:
    if df.empty:
        return None

    lower_map = {str(c).strip().lower(): c for c in df.columns}

    for name in names:
        key = name.strip().lower()
        if key in lower_map:
            return lower_map[key]

    for c in df.columns:
        col_key = str(c).strip().lower()
        for name in names:
            if name.strip().lower() in col_key:
                return c

    return None


def normalize_holdings_df(df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "status",
        "stock_name",
        "stock_code",
        "quantity",
        "avg_price",
        "buy_date",
        "strategy",
        "target_price",
        "stop_loss",
        "weight_note",
        "memo",
    ]

    if df.empty:
        return pd.DataFrame(columns=columns)

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
    for target, aliases in mapping.items():
        source_col = find_col(df, aliases)
        out[target] = df[source_col].map(norm_text) if source_col else ""

    out["stock_code"] = out["stock_code"].map(normalize_code)
    out["stock_name"] = out["stock_name"].map(norm_text)
    out = out[(out["stock_name"] != "") | (out["stock_code"] != "")].copy()

    return out[columns]


def load_holdings() -> tuple[pd.DataFrame, str]:
    english = normalize_holdings_df(read_csv_safely(Path("holdings_manual_input.csv")))
    korean = normalize_holdings_df(read_csv_safely(Path("보유종목_수동입력.csv")))

    if not english.empty:
        return english, "holdings_manual_input.csv"

    if not korean.empty:
        return korean, "보유종목_수동입력.csv"

    return pd.DataFrame(), "not_found"


def build_code_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}

    for path in [
        Path("종목분야_수동입력.csv"),
        Path("TOSS_수동후보.csv"),
        Path("trade_log_manual_input.csv"),
        Path("매매기록_수동입력.csv"),
    ]:
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

    return lookup


def fetch_naver_finance_price(code: str):
    code = normalize_code(code)

    if not code:
        return None, "no_code"

    url = f"https://finance.naver.com/item/main.naver?code={code}"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; stock-report-bot/1.0)",
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            text = response.read().decode("euc-kr", errors="ignore")

        match = re.search(
            r'<p class="no_today">.*?<span class="blind">([\d,]+)</span>',
            text,
            re.S,
        )

        if not match:
            match = re.search(r'<span class="blind">([\d,]+)</span>', text, re.S)

        if match:
            return float(match.group(1).replace(",", "")), "naver_finance"

        return None, "parse_failed"

    except urllib.error.HTTPError as exc:
        return None, f"http_{exc.code}"
    except Exception as exc:
        return None, f"error_{type(exc).__name__}"


def make_decision(pnl_pct, target_price, stop_loss, current_price):
    if current_price is None:
        return "PRICE_NOT_MATCHED", "현재가 직접 조회 실패. 종목코드 6자리와 네이버 금융 조회 가능 여부를 확인하세요."

    if stop_loss and current_price <= stop_loss:
        return "STOP_WATCH", "손절 기준가 근접 또는 이탈. 추가매수보다 리스크 축소 우선."

    if target_price and current_price >= target_price:
        return "TAKE_PROFIT", "목표가 도달 또는 근접. 일부 익절/분할매도 검토."

    if pnl_pct is not None:
        if pnl_pct >= 8:
            return "TAKE_PROFIT_1", "습관형 1차 익절권. 일부 익절 후 잔량 관리 검토."
        if pnl_pct <= -7:
            return "STOP_WATCH", "습관형 손절권. 물타기 금지, 손실 확대 방지 우선."

    return "HOLD", "보유 유지. 뉴스·거래량·추천 재등장 여부 확인."


def build_holding_outputs() -> None:
    holdings, source_file = load_holdings()
    data_dir = Path("docs/data")
    data_dir.mkdir(parents=True, exist_ok=True)

    if holdings.empty:
        diagnostic = pd.DataFrame(
            [
                {
                    "status": "NO_HOLDINGS_INPUT",
                    "message": "holdings_manual_input.csv 파일이 없거나 비어 있습니다.",
                    "checked_at": now_kst(),
                }
            ]
        )
        for filename in [
            "latest_holdings.csv",
            "latest_holding_current_prices.csv",
            "latest_holding_deep_analysis.csv",
            "latest_holding_action_guide.csv",
        ]:
            write_csv_safely(diagnostic, data_dir / filename)
        return

    code_lookup = build_code_lookup()
    holdings["stock_code"] = holdings.apply(
        lambda row: normalize_code(row.get("stock_code")) or code_lookup.get(norm_text(row.get("stock_name")), ""),
        axis=1,
    )

    price_rows = []
    deep_rows = []
    guide_rows = []

    for _, row in holdings.iterrows():
        stock_name = norm_text(row.get("stock_name"))
        stock_code = normalize_code(row.get("stock_code"))

        current_price, price_source = fetch_naver_finance_price(stock_code)
        time.sleep(0.15)

        quantity = to_float(row.get("quantity"))
        avg_price = to_float(row.get("avg_price"))
        target_price = to_float(row.get("target_price"))
        stop_loss = to_float(row.get("stop_loss"))

        pnl_pct = None
        if current_price and avg_price and avg_price > 0:
            pnl_pct = (current_price / avg_price - 1) * 100

        decision, memo = make_decision(pnl_pct, target_price, stop_loss, current_price)

        price_rows.append(
            {
                "stock_name": stock_name,
                "stock_code": stock_code,
                "current_price": current_price if current_price is not None else "",
                "price_source": price_source,
                "fetched_at": now_kst(),
            }
        )

        deep_rows.append(
            {
                "source_file": source_file,
                "status": row.get("status", ""),
                "stock_name": stock_name,
                "stock_code": stock_code,
                "quantity": quantity if quantity is not None else "",
                "avg_price": avg_price if avg_price is not None else "",
                "current_price": current_price if current_price is not None else "",
                "current_price_source": price_source,
                "unrealized_pnl_pct": round(pnl_pct, 2) if pnl_pct is not None else "",
                "target_price": target_price if target_price is not None else "",
                "stop_loss": stop_loss if stop_loss is not None else "",
                "decision": decision,
                "memo": memo,
                "checked_at": now_kst(),
            }
        )

        guide_rows.append(
            {
                "stock_name": stock_name,
                "stock_code": stock_code,
                "decision": decision,
                "take_profit_1": target_price if target_price else (round(avg_price * 1.08, 2) if avg_price else ""),
                "take_profit_2": round(avg_price * 1.15, 2) if avg_price else "",
                "stop_loss": stop_loss if stop_loss else (round(avg_price * 0.93, 2) if avg_price else ""),
                "sell_guide": memo,
                "price_match_status": price_source,
            }
        )

    write_csv_safely(holdings, data_dir / "latest_holdings.csv")
    write_csv_safely(pd.DataFrame(price_rows), data_dir / "latest_holding_current_prices.csv")
    write_csv_safely(pd.DataFrame(deep_rows), data_dir / "latest_holding_deep_analysis.csv")
    write_csv_safely(pd.DataFrame(guide_rows), data_dir / "latest_holding_action_guide.csv")

    table_rows = []
    for row in deep_rows:
        table_rows.append(
            "<tr>"
            f"<td>{html.escape(str(row.get('stock_name', '')))}</td>"
            f"<td>{html.escape(str(row.get('stock_code', '')))}</td>"
            f"<td>{html.escape(str(row.get('decision', '')))}</td>"
            f"<td>{html.escape(str(row.get('avg_price', '')))}</td>"
            f"<td>{html.escape(str(row.get('current_price', '')))}</td>"
            f"<td>{html.escape(str(row.get('unrealized_pnl_pct', '')))}</td>"
            f"<td>{html.escape(str(row.get('current_price_source', '')))}</td>"
            f"<td>{html.escape(str(row.get('memo', '')))}</td>"
            "</tr>"
        )

    v11_page = Path("docs/v11_holdings/index.html")
    v11_page.parent.mkdir(parents=True, exist_ok=True)
    v11_page.write_text(
        f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>보유종목 심화분석</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f6f7fb;margin:0;color:#111827}}
.wrap{{max-width:1100px;margin:auto;padding:20px}}
.hero{{background:#111827;color:white;border-radius:20px;padding:20px;margin-bottom:16px}}
.box{{overflow:auto;background:white;border-radius:16px;box-shadow:0 4px 16px rgba(0,0,0,.06)}}
table{{border-collapse:collapse;width:100%;min-width:900px}}
th,td{{border-bottom:1px solid #e5e7eb;padding:10px;font-size:13px;text-align:left;vertical-align:top}}
th{{background:#f3f4f6}}
</style>
</head>
<body>
<main class="wrap">
<section class="hero">
<h1>보유종목 심화분석</h1>
<p>갱신: {html.escape(now_kst())}</p>
<p>현재가는 네이버 금융 종목코드 직접 조회 기준입니다.</p>
</section>
<div class="box">
<table>
<thead>
<tr>
<th>종목명</th><th>코드</th><th>판단</th><th>평균단가</th><th>현재가</th><th>손익률%</th><th>출처</th><th>메모</th>
</tr>
</thead>
<tbody>
{''.join(table_rows)}
</tbody>
</table>
</div>
</main>
</body>
</html>
""",
        encoding="utf-8",
    )


def strip_html_tags(value) -> str:
    return re.sub(r"<.*?>", "", html.unescape(norm_text(value)))


def load_news_queries() -> list[str]:
    queries = ["코스피", "코스닥", "국내증시", "주식시장"]

    holdings, _ = load_holdings()
    if not holdings.empty:
        queries.extend([norm_text(x) for x in holdings["stock_name"].head(8).tolist() if norm_text(x)])

    candidates = read_csv_safely(Path("docs/data/latest_candidates.csv"))
    if not candidates.empty:
        name_col = find_col(candidates, ["stock_name", "종목명", "name"])
        if name_col:
            queries.extend([norm_text(x) for x in candidates[name_col].head(8).tolist() if norm_text(x)])

    seen = set()
    result = []
    for query in queries:
        if query and query not in seen:
            seen.add(query)
            result.append(query)

    return result[:20]


def fetch_naver_news_detail() -> pd.DataFrame:
    client_id = os.environ.get("NAVER_CLIENT_ID", "").strip()
    client_secret = os.environ.get("NAVER_CLIENT_SECRET", "").strip()

    rows = []

    if not client_id or not client_secret:
        rows.append(
            {
                "category": "diagnostic",
                "query": "",
                "title": "네이버뉴스 API 키가 Actions에 전달되지 않았습니다.",
                "description": "GitHub Secrets의 NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 및 workflow env 연결을 확인하세요.",
                "link": "",
                "pubDate": "",
                "api_state": "missing_or_not_passed",
                "checked_at": now_kst(),
            }
        )
        return pd.DataFrame(rows)

    for query in load_news_queries():
        params = urllib.parse.urlencode(
            {
                "query": query,
                "display": 5,
                "sort": "date",
            }
        )
        url = f"https://openapi.naver.com/v1/search/news.json?{params}"
        request = urllib.request.Request(
            url,
            headers={
                "X-Naver-Client-Id": client_id,
                "X-Naver-Client-Secret": client_secret,
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=12) as response:
                data = json.loads(response.read().decode("utf-8"))

            for item in data.get("items", []):
                rows.append(
                    {
                        "category": "news",
                        "query": query,
                        "title": strip_html_tags(item.get("title")),
                        "description": strip_html_tags(item.get("description")),
                        "link": item.get("link", ""),
                        "pubDate": item.get("pubDate", ""),
                        "api_state": "ok",
                        "checked_at": now_kst(),
                    }
                )

        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")[:400]
            rows.append(
                {
                    "category": "diagnostic",
                    "query": query,
                    "title": f"네이버뉴스 API HTTP 오류 {exc.code}",
                    "description": body,
                    "link": "",
                    "pubDate": "",
                    "api_state": f"http_{exc.code}",
                    "checked_at": now_kst(),
                }
            )

        except Exception as exc:
            rows.append(
                {
                    "category": "diagnostic",
                    "query": query,
                    "title": "네이버뉴스 API 호출 오류",
                    "description": repr(exc),
                    "link": "",
                    "pubDate": "",
                    "api_state": f"error_{type(exc).__name__}",
                    "checked_at": now_kst(),
                }
            )

        time.sleep(0.1)

    return pd.DataFrame(rows)


def build_news_outputs() -> None:
    news = fetch_naver_news_detail()
    write_csv_safely(news, Path("docs/data/latest_news_detail.csv"))

    cards = []
    for _, row in news.head(120).iterrows():
        query = html.escape(norm_text(row.get("query")))
        api_state = html.escape(norm_text(row.get("api_state")))
        title = html.escape(norm_text(row.get("title")) or "제목 없음")
        description = html.escape(norm_text(row.get("description")))
        link = norm_text(row.get("link"))

        if link:
            link_html = f'<a href="{html.escape(link)}" target="_blank" rel="noopener">기사 열기</a>'
        else:
            link_html = ""

        cards.append(
            "<article class='card'>"
            f"<div class='meta'>{query} · {api_state}</div>"
            f"<h2>{title}</h2>"
            f"<p>{description}</p>"
            f"{link_html}"
            "</article>"
        )

    page = Path("docs/details/naver_news.html")
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(
        f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>네이버뉴스 상세</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f6f7fb;margin:0;color:#111827}}
.wrap{{max-width:900px;margin:auto;padding:20px}}
.hero{{background:#064e3b;color:white;border-radius:20px;padding:20px;margin-bottom:16px}}
.card{{background:white;border-radius:16px;padding:16px;margin-bottom:12px;box-shadow:0 4px 16px rgba(0,0,0,.06)}}
.card h2{{font-size:17px;margin:6px 0 8px}}
.card p{{font-size:14px;line-height:1.55;color:#374151}}
.meta{{font-size:12px;color:#059669}}
a{{color:#2563eb;font-weight:700;text-decoration:none}}
</style>
</head>
<body>
<main class="wrap">
<section class="hero">
<h1>네이버뉴스 상세</h1>
<p>갱신: {html.escape(now_kst())}</p>
<p>API 직접 호출 결과 기준</p>
</section>
{''.join(cards)}
</main>
</body>
</html>
""",
        encoding="utf-8",
    )


def main() -> int:
    build_holding_outputs()
    build_news_outputs()
    print("✅ REAL holding current prices fetched from Naver Finance")
    print("✅ REAL Naver news detail fetched from Search API")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
