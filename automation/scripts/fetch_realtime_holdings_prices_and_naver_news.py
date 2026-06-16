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

try:
    from stock_news_disambiguation import build_news_queries, strip_html, extract_publisher, format_pubdate, news_quality_score
except Exception:
    build_news_queries = None
    extract_publisher = lambda link='', originallink='', raw='': ''
    format_pubdate = lambda value: str(value or '')
    news_quality_score = lambda title, description='', pubDate='', publisher='', link='', originallink='': (0, 'fallback')
    def strip_html(x):
        return re.sub(r"<.*?>", "", html.unescape(str(x or "").strip()))

KST = timezone(timedelta(hours=9))

ETF_CODE_OVERRIDES = {
    "ACE 미국우주테크액티브": "0180V0",
}

def normalize_holding_code(stock_name: str, stock_code) -> str:
    name = norm_text(stock_name)
    if name in ETF_CODE_OVERRIDES:
        return ETF_CODE_OVERRIDES[name]
    return normalize_code(stock_code)



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
    text = text.replace(",", "").replace(" ", "").strip().upper()
    if re.fullmatch(r"\d+\.0", text):
        text = text[:-2]
    text = re.sub(r"[^0-9A-Z]", "", text)
    if not text:
        return ""
    if re.fullmatch(r"[0-9A-Z]+", text):
        return text.zfill(6)
    return text


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

    out["stock_code"] = [normalize_holding_code(n, c) for n, c in zip(out.get("stock_name", []), out.get("stock_code", []))]
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
            code = normalize_holding_code(name, row.get(code_col))

            if name and code:
                lookup[name] = code

    return lookup


def format_won(value) -> str:
    num = to_float(value)
    if num is None:
        return "-"
    return f"{int(round(num)):,.0f}원"

def format_pct(value) -> str:
    num = to_float(value)
    if num is None:
        return "-"
    return f"{num:+.2f}%"

def pnl_class(value) -> str:
    num = to_float(value)
    if num is None:
        return "neutral"
    return "profit" if num > 0 else "loss" if num < 0 else "neutral"


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

        patterns = [
            # 일반 주식 현재가
            (r'<p class="no_today">\s*<em[^>]*>\s*<span class="blind">([\d,]+)</span>', 'naver_stock_no_today'),
            (r'<div class="today">.*?<span class="blind">([\d,]+)</span>', 'naver_stock_today'),
            # ETF/ETN/펀드 요약 레이어 또는 rate_info 주변 현재가
            (r'<div class="rate_info">.*?<span class="blind">([\d,]+)</span>', 'naver_rate_info'),
            (r'<em class="no_up">\s*<span class="blind">([\d,]+)</span>', 'naver_etf_up'),
            (r'<em class="no_down">\s*<span class="blind">([\d,]+)</span>', 'naver_etf_down'),
            (r'<span class="blind">([\d,]+)</span>', 'naver_blind_fallback'),
        ]
        for pattern, source in patterns:
            match = re.search(pattern, text, re.S)
            if not match:
                continue
            value = float(match.group(1).replace(',', ''))
            if value > 0:
                return value, source
        return None, "parse_failed"
    except urllib.error.HTTPError as exc:
        return None, f"http_{exc.code}"
    except Exception as exc:
        return None, f"error_{type(exc).__name__}"


def safe_money(value) -> str:
    num = to_float(value)
    if num is None:
        return "-"
    return f"{int(round(num)):,}원"


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



def load_holding_ai_guidance_map() -> dict[str, dict]:
    df = read_csv_safely(Path("docs/data/latest_holding_ai_briefing.csv"))
    out: dict[str, dict] = {}
    if df.empty:
        return out
    for _, r in df.iterrows():
        name = norm_text(r.get("stock_name"))
        if not name:
            continue
        headline = norm_text(r.get("ai_action_headline")) or norm_text(r.get("decision"))
        summary = norm_text(r.get("ai_three_line_summary")) or norm_text(r.get("ai_price_action_guide")) or norm_text(r.get("ai_action_guide")) or norm_text(r.get("ai_issue_summary"))
        out[name] = {"headline": headline, "summary": summary}
    return out

def summarize_news_three_lines(title: str, description: str, qscore="", qreason="") -> str:
    title = strip_html_tags(title)
    desc = strip_html_tags(description)
    text = re.sub(r"\s+", " ", f"{title}. {desc}").strip()
    if not text:
        return "• 기사 요약 데이터가 부족합니다.\n• 원문 링크와 공시 여부를 함께 확인하세요.\n• 단순 시세 기사라면 매매 근거로 약하게 봅니다."
    sents = [x.strip(" .") for x in re.split(r"(?<=[.!?。])\s+|[。]", text) if x.strip()]
    if len(sents) < 3:
        chunks = [text[i:i+80] for i in range(0, min(len(text), 240), 80)]
        sents = chunks
    bullets = []
    labels = ["핵심", "영향", "체크"]
    for idx in range(3):
        val = sents[idx] if idx < len(sents) else ("품질점수와 기사 날짜를 함께 확인해야 합니다." if idx == 2 else "시장 반응과 거래량 확인이 필요합니다.")
        bullets.append(f"• {labels[idx]}: {val[:120]}")
    if qscore != "":
        bullets[2] = bullets[2] + f" / 품질점수 {qscore}"
    return "\n".join(bullets)



def load_toss_holdings_snapshot() -> pd.DataFrame:
    df = read_csv_safely(Path("docs/data/toss_holdings_snapshot.csv"))
    if df.empty:
        return pd.DataFrame()
    if "stock_code" in df.columns:
        df["stock_code"] = [normalize_holding_code(n, c) for n, c in zip(df.get("stock_name", []), df.get("stock_code", []))]
    return df.fillna("")


def load_toss_price_snapshot() -> pd.DataFrame:
    df = read_csv_safely(Path("docs/data/toss_price_snapshot.csv"))
    if df.empty:
        return pd.DataFrame()
    if "stock_code" in df.columns:
        df["stock_code"] = [normalize_holding_code(n, c) for n, c in zip(df.get("stock_name", []), df.get("stock_code", []))]
    return df.fillna("")


def merge_toss_holdings_with_manual(manual: pd.DataFrame, toss_df: pd.DataFrame) -> pd.DataFrame:
    """Prefer Toss account holdings for quantity/avg/current price, preserve manual target/stop/strategy fields."""
    if toss_df.empty or os.environ.get("TOSSINVEST_PREFER_HOLDINGS", "true").lower() not in {"1", "true", "yes", "y"}:
        return manual

    manual_by_code = {}
    manual_by_name = {}
    for _, r in manual.iterrows():
        code = normalize_holding_code(r.get("stock_name"), r.get("stock_code"))
        name = norm_text(r.get("stock_name"))
        if code:
            manual_by_code[code] = r
        if name:
            manual_by_name[name] = r

    rows = []
    for _, tr in toss_df.iterrows():
        name = norm_text(tr.get("stock_name"))
        code = normalize_holding_code(name, tr.get("stock_code"))
        mr = manual_by_code.get(code) or manual_by_name.get(name)
        base = {c: "" for c in [
            "status","stock_name","stock_code","quantity","avg_price","buy_date","strategy","target_price","stop_loss","weight_note","memo"
        ]}
        if mr is not None:
            for c in base.keys():
                base[c] = mr.get(c, "")
        base["status"] = base.get("status") or "holding"
        base["stock_name"] = name or base.get("stock_name", "")
        base["stock_code"] = code or base.get("stock_code", "")
        if norm_text(tr.get("quantity")):
            base["quantity"] = tr.get("quantity")
        if norm_text(tr.get("avg_price")):
            base["avg_price"] = tr.get("avg_price")
        memo = norm_text(base.get("memo"))
        base["memo"] = (memo + " / " if memo else "") + "Toss API 보유수량·평단 우선 반영"
        rows.append(base)

    if rows:
        return normalize_holdings_df(pd.DataFrame(rows))
    return manual


def toss_price_lookup(stock_name: str, stock_code: str, toss_holdings: pd.DataFrame, toss_prices: pd.DataFrame):
    name = norm_text(stock_name)
    code = normalize_holding_code(name, stock_code)

    for df, label in [(toss_prices, "toss_api_price"), (toss_holdings, "toss_api_holding")]:
        if df.empty:
            continue
        for _, r in df.iterrows():
            rname = norm_text(r.get("stock_name"))
            rcode = normalize_holding_code(rname, r.get("stock_code"))
            if (code and rcode == code) or (name and rname == name):
                price = to_float(r.get("current_price"))
                if price:
                    return price, label
    return None, ""


def build_holding_outputs() -> None:
    holdings, source_file = load_holdings()
    data_dir = Path("docs/data")
    data_dir.mkdir(parents=True, exist_ok=True)

    toss_holdings_snapshot = load_toss_holdings_snapshot()
    toss_price_snapshot = load_toss_price_snapshot()
    if not toss_holdings_snapshot.empty:
        holdings = merge_toss_holdings_with_manual(holdings, toss_holdings_snapshot)
        source_file = source_file + " + toss_holdings_snapshot"

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
        lambda row: normalize_holding_code(row.get("stock_name"), row.get("stock_code")) or code_lookup.get(norm_text(row.get("stock_name")), ""),
        axis=1,
    )

    price_rows = []
    deep_rows = []
    guide_rows = []
    ai_guidance_by_name = load_holding_ai_guidance_map()

    for _, row in holdings.iterrows():
        stock_name = norm_text(row.get("stock_name"))
        stock_code = normalize_holding_code(stock_name, row.get("stock_code"))

        current_price, price_source = toss_price_lookup(stock_name, stock_code, toss_holdings_snapshot, toss_price_snapshot)
        if current_price is None:
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

    cards = []
    for row in deep_rows:
        name = html.escape(str(row.get('stock_name', '')))
        code = html.escape(str(row.get('stock_code', '')))
        decision = html.escape(str(row.get('decision', '')))
        avg = format_won(row.get('avg_price'))
        current = format_won(row.get('current_price'))
        target = format_won(row.get('target_price'))
        stop = format_won(row.get('stop_loss'))
        pnl_text = format_pct(row.get('unrealized_pnl_pct'))
        cls = pnl_class(row.get('unrealized_pnl_pct'))
        memo = html.escape(str(row.get('memo', '')))
        source = html.escape(str(row.get('current_price_source', '')))
        ai = ai_guidance_by_name.get(str(row.get('stock_name', '')), {})
        ai_headline = html.escape(str(ai.get('headline') or decision or 'AI 조언 대기'))
        ai_summary = html.escape(str(ai.get('summary') or '장마감 AI 브리핑 생성 후 이 영역에 종목별 실전 조언이 표시됩니다.')).replace('\n', '<br>')
        cards.append(
            "<article class='holding-card'>"
            f"<div class='card-top'><div><h2>{name}</h2><p class='code'>{code}</p></div><span class='badge'>{decision}</span></div>"
            "<div class='metrics'>"
            f"<div><small>평단가</small><b>{avg}</b></div>"
            f"<div><small>현재가</small><b>{current}</b></div>"
            f"<div><small>손익률</small><b class='{cls}'>{pnl_text}</b></div>"
            "</div>"
            "<div class='line'></div>"
            f"<p class='targets'><b>목표가</b> {target} <span></span><b>손절가</b> {stop}</p>"
            f"<p class='memo'>{memo}</p>"
            f"<section class='ai-advice'><b>AI 매니저의 실전 조언 · {ai_headline}</b><p>{ai_summary}</p></section>"
            f"<p class='source'>현재가 출처: {source}</p>"
            "</article>"
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
:root{{color-scheme:light}}
*{{box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f6f7fb;margin:0;color:#111827}}
.wrap{{max-width:920px;margin:auto;padding:18px}}
.hero{{background:linear-gradient(135deg,#111827,#1e3a8a);color:white;border-radius:24px;padding:22px;margin-bottom:16px;box-shadow:0 8px 24px rgba(17,24,39,.18)}}
.hero h1{{margin:0 0 8px;font-size:24px}}
.hero p{{margin:4px 0;color:#dbeafe;line-height:1.55}}
.card-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}}
.holding-card{{background:white;border-radius:22px;padding:17px;box-shadow:0 8px 22px rgba(15,23,42,.08);border:1px solid #e5e7eb}}
.card-top{{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}}
.card-top h2{{font-size:20px;margin:0 0 4px;letter-spacing:-.02em}}
.code{{margin:0;color:#6b7280;font-size:13px}}
.badge{{display:inline-flex;align-items:center;justify-content:center;white-space:nowrap;background:#eef2ff;color:#3730a3;border-radius:999px;padding:7px 10px;font-size:12px;font-weight:800}}
.metrics{{display:grid;grid-template-columns:repeat(3,1fr);gap:9px;margin:16px 0}}
.metrics div{{background:#f9fafb;border-radius:16px;padding:11px;min-width:0}}
.metrics small{{display:block;color:#6b7280;font-size:11px;margin-bottom:5px}}
.metrics b{{font-size:15px;word-break:break-all}}
.profit{{color:#dc2626!important}}.loss{{color:#2563eb!important}}.neutral{{color:#374151!important}}
.line{{height:1px;background:#e5e7eb;margin:12px 0}}
.targets{{display:flex;gap:8px;flex-wrap:wrap;font-size:14px;color:#374151;line-height:1.5}}
.targets span{{width:8px}}
.memo{{background:#fff7ed;color:#9a3412;border-radius:14px;padding:10px;font-size:13px;line-height:1.55}}
.source{{color:#6b7280;font-size:12px;margin-bottom:0}}.ai-advice{{background:#eef2ff;border:1px solid #c7d2fe;color:#1e1b4b;border-radius:16px;padding:12px;margin:12px 0}}.ai-advice b{{font-size:13px}}.ai-advice p{{margin:7px 0 0;font-size:13px;line-height:1.55;color:#312e81}}
@media(max-width:480px){{.wrap{{padding:12px}}.hero{{border-radius:20px;padding:18px}}.card-grid{{display:block}}.holding-card{{margin-bottom:12px;border-radius:20px}}.metrics{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<main class="wrap">
<section class="hero">
<h1>보유종목 심화분석</h1>
<p>갱신: {html.escape(now_kst())}</p>
<p>현재가는 네이버 금융 종목코드 직접 조회 기준입니다. 모든 항목은 모바일 세로 카드형으로 표시됩니다.</p>
</section>
<section class="card-grid">
{''.join(cards)}
</section>
</main>
</body>
</html>
""",
        encoding="utf-8",
    )


def strip_html_tags(value) -> str:
    return strip_html(norm_text(value))


def load_news_queries() -> list[str]:
    queries = ["코스피", "코스닥", "국내증시", "주식시장"]

    holdings, _ = load_holdings()
    if not holdings.empty:
        for _, hrow in holdings.head(8).iterrows():
            hname = norm_text(hrow.get("stock_name"))
            hcode = normalize_holding_code(hname, hrow.get("stock_code"))
            if build_news_queries:
                queries.extend(build_news_queries(hname, hcode))
            elif hname:
                queries.append(hname)

    candidates = read_csv_safely(Path("docs/data/latest_candidates.csv"))
    if not candidates.empty:
        name_col = find_col(candidates, ["stock_name", "종목명", "name"])
        if name_col:
            for _, crow in candidates.head(8).iterrows():
                cname = norm_text(crow.get(name_col))
                ccode_col = find_col(candidates, ["stock_code", "종목코드", "code", "ticker"])
                ccode = normalize_holding_code(cname, crow.get(ccode_col)) if ccode_col else ""
                if build_news_queries:
                    queries.extend(build_news_queries(cname, ccode))
                elif cname:
                    queries.append(cname)

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



def enrich_news_metadata(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    rows = []
    for _, r in df.iterrows():
        row = dict(r)
        link = norm_text(row.get("link"))
        originallink = norm_text(row.get("originallink") or row.get("origin_link"))
        pub_date = norm_text(row.get("pubDate") or row.get("published_at"))
        title = strip_html_tags(row.get("title"))
        desc = strip_html_tags(row.get("description"))
        publisher = norm_text(row.get("publisher")) or extract_publisher(link, originallink)
        qscore, qreason = news_quality_score(title, desc, pub_date, publisher, link, originallink)
        row["title"] = title
        row["description"] = desc
        row["publisher"] = publisher
        row["published_at"] = norm_text(row.get("published_at")) or format_pubdate(pub_date)
        row["news_quality_score"] = qscore
        row["news_quality_reason"] = qreason
        row["news_three_line_summary"] = summarize_news_three_lines(title, desc, qscore, qreason)
        rows.append(row)
    return pd.DataFrame(rows)

def build_news_outputs() -> None:
    news = fetch_naver_news_detail()
    news = enrich_news_metadata(news)
    write_csv_safely(news, Path("docs/data/latest_news_detail.csv"))

    cards = []
    for _, row in news.head(120).iterrows():
        meta_bits = [
            norm_text(row.get("query")),
            norm_text(row.get("publisher")),
            norm_text(row.get("published_at") or row.get("pubDate")),
            ("품질 " + norm_text(row.get("news_quality_score"))) if norm_text(row.get("news_quality_score")) else "",
        ]
        query = html.escape(" · ".join([x for x in meta_bits if x]))
        api_state = html.escape(norm_text(row.get("api_state")))
        title = html.escape(norm_text(row.get("title")) or "제목 없음")
        description = html.escape(norm_text(row.get("description")))
        three = html.escape(norm_text(row.get("news_three_line_summary"))).replace('\n', '<br>')
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
            f"<div class='summary3'><b>이 뉴스의 핵심 3줄 요약</b><p>{three}</p></div>"
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
<title>주요 뉴스 요약</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f6f7fb;margin:0;color:#111827}}
.wrap{{max-width:900px;margin:auto;padding:20px}}
.hero{{background:#064e3b;color:white;border-radius:20px;padding:20px;margin-bottom:16px}}
.card{{background:white;border-radius:16px;padding:16px;margin-bottom:12px;box-shadow:0 4px 16px rgba(0,0,0,.06)}}
.card h2{{font-size:17px;margin:6px 0 8px}}
.card p{{font-size:14px;line-height:1.55;color:#374151}}
.meta{{font-size:12px;color:#059669}}
a{{color:#2563eb;font-weight:700;text-decoration:none}}.summary3{{background:#f8fafc;border-left:4px solid #10b981;border-radius:12px;padding:10px;margin-top:10px}}.summary3 b{{font-size:13px;color:#065f46}}.summary3 p{{margin:6px 0 0;font-size:13px;line-height:1.55;color:#064e3b}}
</style>
</head>
<body>
<main class="wrap">
<section class="hero">
<h1>주요 뉴스 요약</h1>
<p>갱신: {html.escape(now_kst())}</p>
<p>API 직접 호출 결과 기준입니다. 기사 날짜·언론사·품질점수를 함께 표시하며, 오래된 단순 주가마감 기사는 우선순위를 낮춥니다.</p>
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
