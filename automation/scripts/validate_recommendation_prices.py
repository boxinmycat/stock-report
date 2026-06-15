#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# v12.2.25 recommendation realtime price guard

from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone, timedelta
import csv, html, json, re, urllib.request, urllib.parse, urllib.error

KST = timezone(timedelta(hours=9))

DATA = Path("docs/data")
DETAILS = Path("docs/details")

PRICE_FIELDS = [
    "current_price", "현재가",
]
ENTRY_FIELDS = [
    "attack_entry", "base_entry", "conservative_entry", "breakout_entry", "stop_price",
    "공격진입가", "기준진입가", "보수진입가", "돌파진입가", "손절기준가",
]
PLAN_FIELDS = ["take_profit_plan", "stop_loss_plan", "익절계획", "손절계획"]

def now():
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")

def esc(x):
    return html.escape(str(x if x is not None else ""))

def clean(x):
    if x is None: return ""
    s = str(x).strip()
    return "" if s.lower() in {"nan","none","null","nat"} else s

def read_csv(path):
    p = Path(path)
    if not p.exists(): return []
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            with p.open(encoding=enc, newline="") as f:
                return list(csv.DictReader(f))
        except Exception:
            pass
    return []

def write_csv(rows, path):
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    headers = []
    for r in rows:
        for k in r.keys():
            if k not in headers: headers.append(k)
    with p.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for r in rows:
            w.writerow({h: r.get(h, "") for h in headers})

def get(row, *names):
    lower = {str(k).lower(): k for k in row.keys()}
    for n in names:
        if n in row and clean(row.get(n)): return clean(row.get(n))
        k = lower.get(str(n).lower())
        if k and clean(row.get(k)): return clean(row.get(k))
    return ""

def normalize_code(code):
    code = clean(code).replace("=", "").replace('"', "").replace("'", "").replace(",", "").replace(" ", "")
    if not code: return ""
    if re.fullmatch(r"\d+\.0", code): code = code[:-2]
    # Important: ETF alpha codes like 0180V0 must be preserved as-is.
    if re.fullmatch(r"\d+", code): return code.zfill(6)
    return code.upper()

def to_float(v):
    s = clean(v)
    if not s: return None
    s = re.sub(r"[^\d.\-]", "", s)
    if not s or s in {"-", ".", "-."}: return None
    try: return float(s)
    except Exception: return None

def fmt_price(v):
    n = to_float(v)
    if n is None: return clean(v)
    return f"{n:,.0f}"

def fetch_naver_price(code):
    code = normalize_code(code)
    if not code: return None, "NO_CODE"
    headers = {"User-Agent":"Mozilla/5.0"}
    # API endpoint first
    urls = [
        f"https://api.finance.naver.com/service/itemSummary.nhn?itemcode={urllib.parse.quote(code)}",
        f"https://finance.naver.com/item/main.naver?code={urllib.parse.quote(code)}",
    ]
    last_err = ""
    for url in urls:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as res:
                raw = res.read()
            text = raw.decode("utf-8", errors="ignore")
            if "itemSummary" in url:
                try:
                    data = json.loads(text)
                    now_price = data.get("now") or data.get("closePrice") or data.get("price")
                    if now_price:
                        return float(str(now_price).replace(",", "")), "NAVER_API"
                except Exception as e:
                    last_err = f"api_json:{type(e).__name__}"
            else:
                # no_today block is the current price on Naver Finance.
                m = re.search(r'<p class="no_today">.*?<span class="blind">([\d,]+)</span>', text, re.S)
                if not m:
                    m = re.search(r'현재가.*?<span class="blind">([\d,]+)</span>', text, re.S)
                if m:
                    return float(m.group(1).replace(",", "")), "NAVER_HTML"
        except Exception as e:
            last_err = f"{type(e).__name__}:{str(e)[:80]}"
    return None, last_err or "FETCH_FAILED"

def validate_row(row, mismatch_threshold=0.15):
    out = dict(row)
    name = get(out, "stock_name", "종목명")
    code = normalize_code(get(out, "stock_code", "종목코드"))
    out["stock_code"] = code or get(out, "stock_code", "종목코드")
    report_price = to_float(get(out, "current_price_original") or get(out, "current_price", "현재가"))
    realtime, source = fetch_naver_price(code)

    out["price_checked_at"] = now()
    out["realtime_price_source"] = source
    out["realtime_price"] = "" if realtime is None else f"{realtime:.0f}"
    out["current_price_original"] = "" if report_price is None else f"{report_price:.0f}"

    if realtime is None:
        out["price_validation_status"] = "PRICE_UNAVAILABLE"
        out["price_validation_message"] = f"실시간 가격 확인 실패({source}). 진입/익절/손절 전략은 보류합니다."
        out["entry_decision"] = "실시간 가격 확인 실패: 전략 보류"
        out["진입판정"] = "실시간 가격 확인 실패: 전략 보류"
        for f in ENTRY_FIELDS + PLAN_FIELDS:
            if f in out:
                out[f] = "실시간 가격 확인 후 재계산 필요"
        out["strategy_guard"] = "BLOCKED_BY_PRICE_UNAVAILABLE"
        return out

    if report_price is None or report_price <= 0:
        diff_ratio = ""
        mismatch = False
    else:
        diff_ratio = abs(realtime - report_price) / report_price
        mismatch = diff_ratio >= mismatch_threshold

    out["price_diff_pct"] = "" if diff_ratio == "" else f"{diff_ratio*100:.2f}%"

    if mismatch:
        out["price_validation_status"] = "PRICE_MISMATCH"
        out["price_validation_message"] = (
            f"리포트 기준가 {report_price:,.0f}원과 실시간가 {realtime:,.0f}원의 차이가 "
            f"{diff_ratio*100:.1f}%입니다. 기존 진입/익절/손절 전략은 보류합니다."
        )
        # Use realtime price for display, but block strategy fields derived from stale price.
        out["current_price"] = f"{realtime:.0f}"
        out["현재가"] = f"{realtime:.0f}"
        out["entry_decision"] = "가격 검증 실패: 전략 보류"
        out["진입판정"] = "가격 검증 실패: 전략 보류"
        for f in ENTRY_FIELDS + PLAN_FIELDS:
            if f in out:
                out[f] = "가격 재검증 후 재계산 필요"
        out["strategy_guard"] = "BLOCKED_BY_PRICE_MISMATCH"
    else:
        out["price_validation_status"] = "OK"
        out["price_validation_message"] = f"실시간가 {realtime:,.0f}원 기준 검증 통과."
        out["current_price"] = f"{realtime:.0f}"
        out["현재가"] = f"{realtime:.0f}"
        out["strategy_guard"] = "OK"

    return out

def render_top15(rows):
    DETAILS.mkdir(parents=True, exist_ok=True)
    cards = []
    for r in rows[:15]:
        status = get(r, "price_validation_status")
        alert_class = " danger" if status == "PRICE_MISMATCH" else " warn" if status == "PRICE_UNAVAILABLE" else ""
        name = get(r, "stock_name", "종목명")
        code = get(r, "stock_code", "종목코드")
        rank = get(r, "rank", "순위")
        sector = get(r, "sector", "섹터/분야", "분야")
        price = fmt_price(get(r, "current_price", "현재가"))
        score = get(r, "score", "실전점수", "점수")
        desc = get(r, "stock_description", "profile_text_for_display")
        entry_decision = get(r, "entry_decision", "진입판정")
        msg = get(r, "price_validation_message")

        if status == "PRICE_MISMATCH":
            strategy_html = "<p class='blocked'><b>전략 보류:</b> 실시간 가격과 기준가 차이가 커서 공격/기준/보수 진입가, 익절/손절 전략을 숨겼습니다.</p>"
        elif status == "PRICE_UNAVAILABLE":
            strategy_html = "<p class='blocked warnblock'><b>전략 보류:</b> 실시간 가격 확인에 실패해서 공격/기준/보수 진입가, 익절/손절 전략을 숨겼습니다.</p>"
        else:
            strategy_html = f"""
<p><b>공격/기준/보수 진입가:</b> {esc(get(r,'attack_entry','공격진입가'))} / {esc(get(r,'base_entry','기준진입가'))} / {esc(get(r,'conservative_entry','보수진입가'))}</p>
<p><b>돌파 진입가:</b> {esc(get(r,'breakout_entry','돌파진입가'))}<br><b>손절 기준가:</b> {esc(get(r,'stop_price','손절기준가'))}</p>
<p><b>익절:</b> {esc(get(r,'take_profit_plan','익절계획'))}<br><b>손절:</b> {esc(get(r,'stop_loss_plan','손절계획'))}</p>
"""

        cards.append(f"""
<article class='card{alert_class}'>
  <h2>#{esc(rank)} {esc(name)} <span>{esc(code)}</span></h2>
  <div class='meta'>{esc(sector)} · 현재가 {esc(price)}원 · 실전점수 {esc(score)} · {esc(entry_decision)}</div>
  <div class='pricecheck'><b>가격 검증:</b> {esc(status)} · {esc(msg)}</div>
  <pre class='desc'>{esc(desc)}</pre>
  {strategy_html}
</article>""")

    page = f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>추천 TOP15 + 가격 검증</title><style>
body{{margin:0;background:#f6f7fb;color:#111827;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}.wrap{{max-width:1080px;margin:auto;padding:20px}}.hero{{background:#172554;color:white;border-radius:22px;padding:22px;margin-bottom:16px}}.hero p{{color:#dbeafe;line-height:1.55}}.card{{background:white;border-radius:18px;padding:16px;margin-bottom:16px;box-shadow:0 4px 16px #0001;border:1px solid #e5e7eb}}.card.danger{{border-color:#fecaca;background:#fff7f7}}.card.warn{{border-color:#fde68a;background:#fffdf3}}h2{{font-size:20px;margin:0 0 8px}}h2 span{{font-size:12px;color:#6b7280}}.meta,.pricecheck{{font-size:13px;color:#6b7280;line-height:1.55;margin:6px 0}}.pricecheck{{background:#f9fafb;border-radius:10px;padding:10px}}.danger .pricecheck{{background:#fee2e2;color:#991b1b}}.warn .pricecheck{{background:#fef3c7;color:#92400e}}p{{font-size:14px;line-height:1.65;color:#374151}}.blocked{{background:#fee2e2;color:#991b1b;border-radius:10px;padding:10px}}.desc{{white-space:pre-wrap;background:#f8fafc;border-radius:12px;padding:12px;font-size:13px;line-height:1.62;color:#374151}}</style></head><body><main class='wrap'><section class='hero'><h1>추천 TOP15 + 실시간 가격 검증</h1><p>갱신: {esc(now())}<br>실시간 가격과 리포트 기준 가격 차이가 15% 이상이면 해당 종목의 진입/익절/손절 전략을 보류합니다.</p></section>{''.join(cards)}</main></body></html>"""
    (DETAILS / "legacy_top15.html").write_text(page, encoding="utf-8")
    (DETAILS / "recommendation_top15.html").write_text(page, encoding="utf-8")

def main():
    DATA.mkdir(parents=True, exist_ok=True)
    top_path = DATA / "latest_recommendation_top15_full.csv"
    rows = read_csv(top_path)
    if not rows:
        write_csv([{"status":"NO_TOP15", "checked_at":now()}], DATA/"latest_price_validation.csv")
        print("⚠️ no TOP15 rows for price validation")
        return 0

    validated = [validate_row(r) for r in rows]
    write_csv(validated, top_path)
    write_csv(validated, DATA / "latest_recommendation_analysis.csv")
    write_csv(validated, DATA / "latest_price_validation.csv")
    render_top15(validated)

    bad = [r for r in validated if get(r,"price_validation_status") == "PRICE_MISMATCH"]
    print(f"✅ recommendation price validation complete. rows={len(validated)}, mismatch={len(bad)}")
    for r in bad[:10]:
        print(f"PRICE_MISMATCH: {get(r,'stock_name')} {get(r,'stock_code')} :: {get(r,'price_validation_message')}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
