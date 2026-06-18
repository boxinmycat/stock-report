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
    extract_publisher = lambda link='', originallink='', raw='': '주요언론사'
    format_pubdate = lambda value: str(value or '')
    news_quality_score = lambda title, description='', pubDate='', publisher='', link='', originallink='': (50, 'fallback')
    def strip_html(x): return re.sub(r"<.*?>", "", html.unescape(str(x or "").strip()))

KST = timezone(timedelta(hours=9))

# [시세 오류 박멸] 네이버 금융 규격 숫자인 6자리 코드로 정밀 동기화
ETF_CODE_OVERRIDES = {
    "ACE 미국우주테크액티브": "414250",
}

def normalize_holding_code(stock_name: str, stock_code) -> str:
    name = norm_text(stock_name)
    if name in ETF_CODE_OVERRIDES: return ETF_CODE_OVERRIDES[name]
    return normalize_code(stock_code)

def now_kst() -> str: return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")

def read_csv_safely(path: Path) -> pd.DataFrame:
    if not path.exists(): return pd.DataFrame()
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try: return pd.read_csv(path, dtype=str, encoding=enc).fillna("")
        except: pass
    return pd.DataFrame()

def write_csv_safely(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.fillna("").to_csv(path, index=False, encoding="utf-8-sig")

def norm_text(value) -> str:
    if value is None: return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "null"} else text

def normalize_code(value) -> str:
    text = norm_text(value)
    if not text: return ""
    text = text.replace("=", "").replace('"', "").replace("'", "").replace(",", "").replace(" ", "").strip().upper()
    if text.endswith(".0"): text = text[:-2]
    text = re.sub(r"[^0-9A-Z]", "", text)
    return text.zfill(6) if re.fullmatch(r"[0-9A-Z]+", text) else text

def to_float(value):
    text = norm_text(value)
    if not text: return None
    text = re.sub(r"[^\d\.\-]", "", text)
    try: return float(text)
    except: return None

def find_col(df: pd.DataFrame, names: list[str]) -> str | None:
    if df.empty: return None
    lower_map = {str(c).strip().lower(): c for c in df.columns}
    for name in names:
        key = name.strip().lower()
        if key in lower_map: return lower_map[key]
    return None

def normalize_holdings_df(df: pd.DataFrame) -> pd.DataFrame:
    columns = ["status", "stock_name", "stock_code", "quantity", "avg_price", "buy_date", "strategy", "target_price", "stop_loss", "weight_note", "memo"]
    if df.empty: return pd.DataFrame(columns=columns)
    mapping = {"status": ["status", "상태"], "stock_name": ["stock_name", "종목명", "name"], "stock_code": ["stock_code", "종목코드"], "quantity": ["quantity", "보유수량"], "avg_price": ["avg_price", "평균단가"], "buy_date": ["buy_date", "매수일"], "strategy": ["strategy", "전략구분"], "target_price": ["target_price", "목표가"], "stop_loss": ["stop_loss", "손절가"], "weight_note": ["weight_note", "비중메모"], "memo": ["memo", "메모"]}
    out = pd.DataFrame()
    for target, aliases in mapping.items():
        source_col = find_col(df, aliases)
        out[target] = df[source_col].map(norm_text) if source_col else ""
    out["stock_code"] = [normalize_holding_code(n, c) for n, c in zip(out.get("stock_name", []), out.get("stock_code", []))]
    return out[(out["stock_name"] != "") | (out["stock_code"] != "")].copy()[columns]

def load_holdings() -> tuple[pd.DataFrame, str]:
    e = normalize_holdings_df(read_csv_safely(Path("holdings_manual_input.csv")))
    if not e.empty: return e, "holdings_manual_input.csv"
    k = normalize_holdings_df(read_csv_safely(Path("보유종목_수동입력.csv")))
    return k, "보유종목_수동입력.csv" if not k.empty else (pd.DataFrame(), "not_found")

def build_code_lookup() -> dict[str, str]:
    lookup = {}
    for path in [Path("종목분야_수동입력.csv"), Path("TOSS_수동후보.csv"), Path("trade_log_manual_input.csv")]:
        df = read_csv_safely(path)
        nc, cc = find_col(df, ["stock_name", "종목명"]), find_col(df, ["stock_code", "종목코드"])
        if nc and cc:
            for _, row in df.iterrows():
                n, c = norm_text(row.get(nc)), normalize_holding_code(row.get(nc), row.get(cc))
                if n and c: lookup[n] = c
    return lookup

def format_won(value) -> str:
    num = to_float(value)
    return "-" if num is None else f"{int(round(num)):,.0f}원"

def format_pct(value) -> str:
    num = to_float(value)
    return "-" if num is None else f"{num:+.2f}%"

def pnl_class(value) -> str:
    num = to_float(value)
    return "neutral" if num == 0 or num is None else "profit" if num > 0 else "loss"

def fetch_naver_finance_price(code: str):
    code = normalize_code(code)
    if not code: return None, "no_code"
    url = f"https://finance.naver.com/item/main.naver?code={code}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            text = resp.read().decode("euc-kr", errors="ignore")
        patterns = [
            (r'<p class="no_today">\s*<em[^>]*>\s*<span class="blind">([\d,]+)</span>', 'naver_stock_no_today'),
            (r'<div class="today">.*?<span class="blind">([\d,]+)</span>', 'naver_stock_today'),
            (r'<div class="rate_info">.*?<span class="blind">([\d,]+)</span>', 'naver_rate_info'),
            (r'<em class="no_up">\s*<span class="blind">([\d,]+)</span>', 'naver_etf_up'),
            (r'<em class="no_down">\s*<span class="blind">([\d,]+)</span>', 'naver_etf_down')
        ]
        for p, src in patterns:
            m = re.search(p, text, re.S)
            if m:
                val = float(m.group(1).replace(',', ''))
                if val > 0: return val, src
        return None, "parse_failed"
    except: return None, "error"

def make_decision(pnl_pct, target_price, stop_loss, current_price):
    if current_price is None: return "PRICE_NOT_MATCHED", "현재가 직접 조회 실패."
    if stop_loss and current_price <= stop_loss: return "🚨 손절검토", "손절 기준가 이탈 우려. 리스크 축소 요망."
    if target_price and current_price >= target_price: return "🎯 일부익절", "목표가 도달. 분할 익절 검토."
    if pnl_pct is not None:
        if pnl_pct >= 8: return "🎯 습관익절", "습관형 익절권 진입."
        if pnl_pct <= -7: return "🚨 리스크축소", "손실 가이드라인 초과. 물타기 금지."
    return "HOLD", "보유 유지. 실시간 거래량 추이 파악 요망."

def load_holding_ai_guidance_map() -> dict[str, dict]:
    df = read_csv_safely(Path("docs/data/latest_holding_ai_briefing.csv"))
    out = {}
    if df.empty: return out
    for _, r in df.iterrows():
        name = norm_text(r.get("stock_name"))
        if name: out[name] = {"headline": norm_text(r.get("ai_action_headline")), "summary": norm_text(r.get("ai_three_line_summary"))}
    return out

def summarize_news_three_lines(title: str, description: str, qscore="", qreason="") -> str:
    t, d = strip_html_tags(title), strip_html_tags(description)
    text = re.sub(r"\s+", " ", f"{t}. {d}").strip()
    sents = [x.strip(" .") for x in re.split(r"(?<=[.!?。])\s+|[。]", text) if x.strip()]
    bullets = [f"• 핵심: {sents[0][:120] if len(sents)>0 else t}", f"• 영향: {sents[1][:120] if len(sents)>1 else '공시 모멘텀 추적 필요'}", f"• 체크: {sents[2][:120] if len(sents)>2 else '수급 강도 관찰'}"]
    if qscore: bullets[2] += f" / 품질 {qscore}점"
    return "\n".join(bullets)

def load_toss_holdings_snapshot() -> pd.DataFrame:
    df = read_csv_safely(Path("docs/data/toss_holdings_snapshot.csv"))
    if not df.empty and "stock_code" in df.columns:
        df["stock_code"] = [normalize_holding_code(n, c) for n, c in zip(df.get("stock_name", []), df.get("stock_code", []))]
    return df

def load_toss_price_snapshot() -> pd.DataFrame:
    df = read_csv_safely(Path("docs/data/toss_price_snapshot.csv"))
    if not df.empty and "stock_code" in df.columns:
        df["stock_code"] = [normalize_holding_code(n, c) for n, c in zip(df.get("stock_name", []), df.get("stock_code", []))]
    return df

def merge_toss_holdings_with_manual(manual: pd.DataFrame, toss_df: pd.DataFrame) -> pd.DataFrame:
    if toss_df.empty or os.environ.get("TOSSINVEST_PREFER_HOLDINGS", "true").lower() not in {"1", "true"}: return manual
    m_by_code = {normalize_holding_code(r.get("stock_name"), r.get("stock_code")): r for _, r in manual.iterrows() if normalize_holding_code(r.get("stock_name"), r.get("stock_code"))}
    rows = []
    for _, tr in toss_df.iterrows():
        n, c = norm_text(tr.get("stock_name")), normalize_holding_code(tr.get("stock_name"), tr.get("stock_code"))
        mr = m_by_code.get(c)
        base = {x: "" for x in ["status","stock_name","stock_code","quantity","avg_price","buy_date","strategy","target_price","stop_loss","weight_note","memo"]}
        if mr is not None:
            for k in base.keys(): base[k] = mr.get(k, "")
        base["status"] = base.get("status") or "holding"
        base["stock_name"], base["stock_code"] = n, c
        if norm_text(tr.get("quantity")): base["quantity"] = tr.get("quantity")
        if norm_text(tr.get("avg_price")): base["avg_price"] = tr.get("avg_price")
        base["memo"] = (str(base["memo"]) + " / " if base["memo"] else "") + "Toss API 연동"
        rows.append(base)
    return normalize_holdings_df(pd.DataFrame(rows)) if rows else manual

def toss_price_lookup(stock_name: str, stock_code: str, toss_holdings: pd.DataFrame, toss_prices: pd.DataFrame):
    n, c = norm_text(stock_name), normalize_holding_code(stock_name, stock_code)
    for df, lbl in [(toss_prices, "toss_api_price"), (toss_holdings, "toss_api_holding")]:
        if df.empty: continue
        for _, r in df.iterrows():
            if (c and normalize_holding_code(r.get("stock_name"), r.get("stock_code")) == c) or (n and norm_text(r.get("stock_name")) == n):
                p = to_float(r.get("current_price"))
                if p: return p, lbl
    return None, ""

def build_holding_outputs() -> None:
    holdings, src_file = load_holdings()
    data_dir = Path("docs/data")
    t_hold, t_price = load_toss_holdings_snapshot(), load_toss_price_snapshot()
    if not t_hold.empty: holdings = merge_toss_holdings_with_manual(holdings, t_hold)
    if holdings.empty: return
    
    cl = build_code_lookup()
    holdings["stock_code"] = [normalize_holding_code(r.get("stock_name"), r.get("stock_code")) or cl.get(norm_text(r.get("stock_name")), "") for _, r in holdings.iterrows()]
    
    p_rows, d_rows, g_rows = [], [], []
    ai_map = load_holding_ai_guidance_map()
    cards = []
    
    for _, row in holdings.iterrows():
        sname = norm_text(row.get("stock_name"))
        scode = normalize_holding_code(sname, row.get("stock_code"))
        cp, psrc = toss_price_lookup(sname, scode, t_hold, t_price)
        if cp is None: cp, psrc = fetch_naver_finance_price(scode); time.sleep(0.1)
        
        qty, avg, tp, sl = to_float(row.get("quantity")), to_float(row.get("avg_price")), to_float(row.get("target_price")), to_float(row.get("stop_loss"))
        pnl = ((cp / avg - 1) * 100) if cp and avg and avg > 0 else None
        dec, memo = make_decision(pnl, tp, sl, cp)
        
        p_rows.append({"stock_name": sname, "stock_code": scode, "current_price": cp or "", "price_source": psrc, "fetched_at": now_kst()})
        d_rows.append({"source_file": src_file, "status": row.get("status",""), "stock_name": sname, "stock_code": scode, "quantity": qty or "", "avg_price": avg or "", "current_price": cp or "", "current_price_source": psrc, "unrealized_pnl_pct": round(pnl, 2) if pnl else "", "target_price": tp or "", "stop_loss": sl or "", "decision": dec, "memo": memo, "checked_at": now_kst()})
        g_rows.append({"stock_name": sname, "stock_code": scode, "decision": dec, "take_profit_1": tp or (round(avg*1.08,2) if avg else ""), "take_profit_2": round(avg*1.15,2) if avg else "", "stop_loss": sl or (round(avg*0.93,2) if avg else ""), "sell_guide": memo, "price_match_status": psrc})
        
        ai = ai_map.get(sname, {})
        ai_head = html.escape(str(ai.get('headline') or dec))
        ai_sum = html.escape(str(ai.get('summary') or '장마감 후 AI 상세 매매 가이드가 반영됩니다.')).replace('\n', '<br>')
        
        qty_display_text = f"{int(qty)}주" if qty else "-"
        
        cards.append(
            f"<article class='holding-card'>"
            f"<div class='card-top'><div><h2>{html.escape(sname)}</h2><p class='code'>{scode}</p></div><span class='badge'>{ai_head}</span></div>"
            f"<div class='metrics'>"
            f"<div><small>평단가 / 수량</small><b>{format_won(avg)} / {qty_display_text}</b></div>"
            f"<div><small>현재가</small><b>{format_won(cp)}</b></div>"
            f"<div><small>손익률</small><b class='{pnl_class(pnl)}'>{format_pct(pnl)}</b></div>"
            f"</div>"
            f"<div class='line'></div>"
            f"<p class='targets'><b>목표가</b> {format_won(tp)} <span style='width:16px;'></span><b>손절가</b> <span style='color:#dc2626; font-weight:bold;'>{format_won(sl)}</span></p>"
            f"<p class='memo'>📋 장부메모: {html.escape(memo)}</p>"
            f"<section class='ai-advice'><b>💡 AI 부서 실전 판단</b><p>{ai_sum}</p></section>"
            f"</article>"
        )
        
    write_csv_safely(pd.DataFrame(p_rows), data_dir / "latest_holding_current_prices.csv")
    write_csv_safely(pd.DataFrame(d_rows), data_dir / "latest_holding_deep_analysis.csv")
    write_csv_safely(pd.DataFrame(g_rows), data_dir / "latest_holding_action_guide.csv")
    
    Path("docs/v11_holdings/index.html").write_text(f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>보유종목 대시보드</title><style>:root{{color-scheme:light}}*{{box-sizing:border-box}}body{{font-family:-apple-system,BlinkMacSystemFont,"Malgun Gothic",sans-serif;background:#f3f4f6;margin:0;padding:12px}}
    .wrap{{max-width:480px;margin:0 auto}}.hero{{background:linear-gradient(135deg,#1e3a8a,#1e40af);color:white;border-radius:14px;padding:14px;margin-bottom:12px}}.hero h1{{margin:0;font-size:18px}}.card-grid{{display:flex;flex-direction:column;gap:10px}}.holding-card{{background:white;border-radius:14px;padding:12px;box-shadow:0 2px 4px rgba(0,0,0,0.02);border:1px solid #e5e7eb;border-left:5px solid #2563eb}}.card-top{{display:flex;justify-content:space-between;align-items:flex-start}}.card-top h2{{font-size:15px;margin:0}}.code{{color:#6b7280;font-size:11px;margin:2px 0}}.badge{{background:#eef2ff;color:#3730a3;border-radius:6px;padding:4px 6px;font-size:11px;font-weight:800}}.metrics{{display:grid;grid-template-columns:1fr;gap:6px;margin:10px 0}}@media(min-width:360px){{.metrics{{grid-template-columns:repeat(3,1fr)}}}}.metrics div{{background:#f9fafb;border-radius:8px;padding:6px;text-align:center}}.metrics small{{display:block;color:#6b7280;font-size:10px}}.metrics b{{font-size:12px}}.profit{{color:#dc2626}}.loss{{color:#2563eb}}.neutral{{color:#374151}}.line{{height:1px;background:#f1f5f9;margin:6px 0}}.targets{{font-size:12px;color:#374151;margin:4px 0;display:flex}}.memo{{background:#fff7ed;color:#9a3412;border-radius:8px;padding:6px;font-size:11px;margin:4px 0}}.ai-advice{{background:#f0fdf4;border:1px solid #bbf7d0;color:#14532d;border-radius:8px;padding:8px;margin-top:6px}}.ai-advice b{{font-size:11px;display:block}}.ai-advice p{{margin:0;font-size:11px;line-height:1.4}}</style></head><body><main class="wrap"><section class="hero"><h1>📊 보유 계좌 자산 실시간 관제</h1><p>갱신: {now_kst()}</p></section><section class="card-grid">{"".join(cards)}</section></main></body></html>""", encoding="utf-8")

def strip_html_tags(value) -> str: return strip_html(norm_text(value))

def load_news_queries() -> list[str]:
    q = ["코스피", "코스닥", "국내증시"]
    hd, _ = load_holdings()
    if not hd.empty: q.extend([norm_text(r.get("stock_name")) for _, r in hd.head(5).iterrows() if norm_text(r.get("stock_name"))])
    return list(set([x for x in q if x]))[:15]

def fetch_naver_news_detail() -> pd.DataFrame:
    cid, csec = os.environ.get("NAVER_CLIENT_ID","").strip(), os.environ.get("NAVER_CLIENT_SECRET","").strip()
    if not cid or not csec: return pd.DataFrame([{"category": "diagnostic", "title": "API 키 확인 필요", "checked_at": now_kst()}])
    rows = []
    for query in load_news_queries():
        p = urllib.parse.urlencode({"query": query, "display": 4, "sort": "date"})
        req = urllib.request.Request(f"https://openapi.naver.com/v1/search/news.json?{p}", headers={"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": csec})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode("utf-8"))
            for item in data.get("items", []):
                rows.append({"category": "news", "query": query, "title": strip_html_tags(item.get("title")), "description": strip_html_tags(item.get("description")), "link": item.get("link", ""), "pubDate": item.get("pubDate", ""), "api_state": "ok"})
        except: pass
    return pd.DataFrame(rows)

def enrich_news_metadata(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty: return df
    rows = []
    for _, r in df.iterrows():
        row = dict(r)
        lk, pub, t, d = norm_text(row.get("link")), norm_text(row.get("pubDate")), strip_html_tags(row.get("title")), strip_html_tags(row.get("description"))
        press = extract_publisher(lk) or "주요언론"
        score, reason = news_quality_score(t, d, pub, press, lk, lk)
        row.update({"title": t, "description": d, "publisher": press, "published_at": format_pubdate(pub), "news_quality_score": str(score), "news_three_line_summary": summarize_news_three_lines(t, d, score)})
        rows.append(row)
    return pd.DataFrame(rows)

def build_news_outputs() -> None:
    news = enrich_news_metadata(fetch_naver_news_detail())
    if news.empty: return
    write_csv_safely(news, Path("docs/data/latest_news_detail.csv"))
    cards = []
    for _, r in news.head(40).iterrows():
        three = html.escape(str(r.get("news_three_line_summary"))).replace('\n', '<br>')
        cards.append(f"<article class='news-card'><div class='meta'>{html.escape(r.get('publisher'))} · 품질 {r.get('news_quality_score')}점</div><h2>{html.escape(r.get('title'))}</h2><p class='body-text'>{html.escape(r.get('description'))}</p><div class='summary3-box'><b>📌 뉴스 핵심 3줄 압축 요약</b><p>{three}</p></div></article>")
    
    Path("docs/details/naver_news.html").write_text(f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>주요 뉴스 브리핑</title><style>body{{font-family:-apple-system,BlinkMacSystemFont,sans-serif;background:#f3f4f6;margin:0;padding:12px}}.wrap{{max-width:480px;margin:auto;padding:20px}}.hero{{background:#064e3b;color:white;border-radius:14px;padding:14px;margin-bottom:12px}}.news-card{{background:white;border-radius:14px;padding:12px;margin-bottom:10px;box-shadow:0 2px 4px rgba(0,0,0,0.02);display:flex;flex-direction:column;gap:4px}}.meta{{font-size:11px;color:#059669;font-weight:600}}.news-card h2{{font-size:14px;margin:2px 0;line-height:1.4}}.body-text{{font-size:12px;color:#4b5563;margin:0}}.summary3-box{{background:#f0fdf4;border-left:4px solid #10b981;padding:8px;border-radius:6px;font-size:11px}}.summary3-box b{{color:#14532d;display:block;margin-bottom:2px}}</style></head><body><main class="wrap"><section class="hero"><h1>📰 실시간 마켓 뉴스 3줄 브리핑</h1><p>갱신: {now_kst()}</p></section>{"".join(cards)}</main></body></html>""", encoding="utf-8")

if __name__ == "__main__":
    build_holding_outputs()
    build_news_outputs()
