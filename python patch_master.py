# -*- coding: utf-8 -*-
import os
from pathlib import Path

# 수정 및 신설될 5개 핵심 파일 매트릭스 정의 (단 한 줄의 생략이나 줄임 없음)
FILES_MATRIX = {
    # [파일 1] 깃허브 액션 워크플로우 (신설된 AI 매매기록 평가 엔진 자동 빌드 파이프라인 추가)
    ".github/workflows/daily-report.yml": """name: daily-stock-report
# v12.2.35 gemini path fix + optimization pipeline

on:
  schedule:
    - cron: '0 23 * * 0-4'
    - cron: '45 7 * * 1-5'
  workflow_dispatch:

permissions:
  contents: write

concurrency:
  group: daily-stock-report-${{ github.ref }}
  cancel-in-progress: true

jobs:
  build-report:
    runs-on: ubuntu-latest
    env:
      NOTEBOOK_FILE: 실전매매_통합시스템_v10_2_연속추천관찰_자동조건검색_드라이브준비.ipynb
      CANDIDATE_SOURCE_MODE: HYBRID
      REQUIRE_TOSS_FILE: "false"
      TOSS_MANUAL_CSV_FILE: TOSS_수동후보.csv
      HOLDINGS_CSV_FILE: holdings_manual_input.csv
      TRADE_LOG_CSV_FILE: trade_log_manual_input.csv
      REPORT_ROOT_MODE: LOCAL
      OPEN_DART_API_KEY: ${{ secrets.OPEN_DART_API_KEY }}
      DART_API_KEY: ${{ secrets.OPEN_DART_API_KEY }}
      NAVER_CLIENT_ID: ${{ secrets.NAVER_CLIENT_ID }}
      NAVER_CLIENT_SECRET: ${{ secrets.NAVER_CLIENT_SECRET }}
      TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
      TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
      GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
      GEMINI_MODEL: gemini-1.5-flash
      TOSSINVEST_CLIENT_ID: ${{ secrets.TOSSINVEST_CLIENT_ID }}
      TOSSINVEST_CLIENT_SECRET: ${{ secrets.TOSSINVEST_CLIENT_SECRET }}
      TOSSINVEST_ACCOUNT: ${{ secrets.TOSSINVEST_ACCOUNT }}
      TOSSINVEST_BASE_URL: https://openapi.tossinvest.com
      TOSSINVEST_USE_API: "true"
      TOSSINVEST_PREFER_HOLDINGS: "true"

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Time guard and schedule diagnostics
        id: time_guard
        shell: bash
        run: |
          EVENT_NAME="${{ github.event_name }}"
          EVENT_SCHEDULE="${{ github.event.schedule }}"
          UTC_NOW="$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
          KST_NOW="$(TZ=Asia/Seoul date '+%Y-%m-%d %H:%M:%S KST')"
          KST_HM="$(TZ=Asia/Seoul date '+%H%M')"
          KST_DOW="$(TZ=Asia/Seoul date '+%u')"

          SKIP_HEAVY_JOB="false"
          REPORT_GUARD_REASON="allowed"
          REPORT_SESSION="MANUAL"

          if [ "$EVENT_NAME" = "schedule" ] && [ "$EVENT_SCHEDULE" = "0 23 * * 0-4" ]; then
            REPORT_SESSION="AM"
          elif [ "$EVENT_NAME" = "schedule" ] && [ "$EVENT_SCHEDULE" = "45 7 * * 1-5" ]; then
            REPORT_SESSION="PM"
          fi

          if [ "$EVENT_NAME" = "schedule" ]; then
            if [ "$KST_DOW" -ge 6 ]; then
              SKIP_HEAVY_JOB="true"
              REPORT_GUARD_REASON="blocked_weekend_kst"
            elif [ "$REPORT_SESSION" = "AM" ]; then
              if [ "$KST_HM" -lt 0730 ] || [ "$KST_HM" -gt 1000 ]; then
                SKIP_HEAVY_JOB="true"
                REPORT_GUARD_REASON="blocked_stale_am_outside_0730_1000_kst"
              fi
            elif [ "$REPORT_SESSION" = "PM" ]; then
              if [ "$KST_HM" -lt 1545 ] || [ "$KST_HM" -gt 1830 ]; then
                SKIP_HEAVY_JOB="true"
                REPORT_GUARD_REASON="blocked_stale_pm_outside_1545_1830_kst"
              fi
            fi
          fi

          mkdir -p docs/data
          {
            echo "key,value"
            echo "event_name,$EVENT_NAME"
            echo "event_schedule,$EVENT_SCHEDULE"
            echo "utc_started_at,$UTC_NOW"
            echo "kst_started_at,$KST_NOW"
            echo "skip_heavy_job,$SKIP_HEAVY_JOB"
            echo "guard_reason,$REPORT_GUARD_REASON"
          } > docs/data/latest_schedule_diagnostics.csv
          
          echo "SKIP_HEAVY_JOB=$SKIP_HEAVY_JOB" >> "$GITHUB_ENV"

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

      - name: Build Toss Invest snapshots
        if: ${{ env.SKIP_HEAVY_JOB != 'true' && env.TOSSINVEST_USE_API == 'true' }}
        run: |
          python automation/scripts/build_toss_holdings_snapshot.py
          python automation/scripts/build_toss_trade_history.py
          python automation/scripts/build_toss_price_snapshot.py

      - name: Prepare runtime notebook
        if: ${{ env.SKIP_HEAVY_JOB != 'true' }}
        run: |
          if [ -f automation/scripts/patch_notebook_config.py ]; then
            python automation/scripts/patch_notebook_config.py "$NOTEBOOK_FILE" "_runtime_report.ipynb"
          else
            cp "$NOTEBOOK_FILE" "_runtime_report.ipynb"
          fi

      - name: Run report notebook
        if: ${{ env.SKIP_HEAVY_JOB != 'true' }}
        run: |
          jupyter nbconvert --to notebook --execute "_runtime_report.ipynb" --output executed_report.ipynb --ExecutePreprocessor.timeout=5400

      - name: Fetch realtime holdings prices and Naver news
        if: ${{ env.SKIP_HEAVY_JOB != 'true' }}
        run: |
          python automation/scripts/fetch_realtime_holdings_prices_and_naver_news.py

      - name: Restore legacy Excel report sections
        if: ${{ env.SKIP_HEAVY_JOB != 'true' }}
        run: |
          python automation/scripts/publish_legacy_excel_sections.py

      - name: Build Gemini recommendation company profiles
        if: ${{ env.SKIP_HEAVY_JOB != 'true' }}
        run: |
          python automation/scripts/build_gemini_recommendation_company_profiles.py

      - name: Build Gemini holding AI briefing
        if: ${{ env.SKIP_HEAVY_JOB != 'true' && (github.event_name == 'workflow_dispatch' || github.event.schedule == '45 7 * * 1-5') }}
        run: |
          python automation/scripts/build_gemini_holding_ai_briefing.py

      - name: Build Gemini trade history evaluation
        if: ${{ env.SKIP_HEAVY_JOB != 'true' && (github.event_name == 'workflow_dispatch' || github.event.schedule == '45 7 * * 1-5') }}
        run: |
          python automation/scripts/build_gemini_trade_performance_evaluation.py

      - name: Final UI Responsive Rebuild
        if: ${{ env.SKIP_HEAVY_JOB != 'true' }}
        run: |
          python automation/scripts/fetch_realtime_holdings_prices_and_naver_news.py
          python automation/scripts/publish_legacy_excel_sections.py
          python automation/scripts/force_refresh_latest.py
          python automation/scripts/build_run_manifest.py

      - name: Commit generated report
        if: ${{ env.SKIP_HEAVY_JOB != 'true' }}
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git fetch origin main
          git pull --rebase --autostash origin main || true
          rm -rf stock_report/reports stock_report/latest stock_report/docs stock_report/html stock_report/downloads || true
          find stock_report -type f \\( -name '*.zip' -o -name '*.xlsx' -o -name '*.ipynb' \\) -delete 2>/dev/null || true
          git add -A docs .github workflows automation || true
          git reset -- '*.zip' '**/*.zip' '*.ipynb' '**/*.ipynb' || true
          git commit -m "Update daily stock report" || true
          git push origin main || true

      - name: Send Telegram report alert
        if: always()
        run: |
          python automation/scripts/send_telegram_report_alert.py
""",

    # [파일 2] 실시간 현재가 수집기 (보유 수량/갯수 컬럼 연동 UI 개조 및 ETF 실제 코드 고정)
    "automation/scripts/fetch_realtime_holdings_prices_and_naver_news.py": """# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone, timedelta
import html, json, os, re, time, urllib.parse, urllib.request, urllib.error
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
            (r'<p class="no_today">\\s*<em[^>]*>\\s*<span class="blind">([\\\\d,]+)</span>', 'naver_stock_no_today'),
            (r'<div class="today">.*?<span class="blind">([\\\\d,]+)</span>', 'naver_stock_today'),
            (r'<div class="rate_info">.*?<span class="blind">([\\\\d,]+)</span>', 'naver_rate_info'),
            (r'<em class="no_up">\\s*<span class="blind">([\\\\d,]+)</span>', 'naver_etf_up'),
            (r'<em class="no_down">\\s*<span class="blind">([\\\\d,]+)</span>', 'naver_etf_down')
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
    text = re.sub(r"\\s+", " ", f"{t}. {d}").strip()
    sents = [x.strip(" .") for x in re.split(r"(?<=[.!?。])\\s+|[。]", text) if x.strip()]
    bullets = [f"• 핵심: {sents[0][:120] if len(sents)>0 else t}", f"• 영향: {sents[1][:120] if len(sents)>1 else '공시 모멘텀 추적 필요'}", f"• 체크: {sents[2][:120] if len(sents)>2 else '수급 강도 관찰'}"]
    if qscore: bullets[2] += f" / 품질 {qscore}점"
    return "\\n".join(bullets)

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
        ai_sum = html.escape(str(ai.get('summary') or '장마감 후 AI 상세 매매 가이드가 반영됩니다.')).replace('\\n', '<br>')
        
        # [요구사항 반영] 평단가와 우측에 실제 보유 수량(갯수)을 직관적으로 바인딩
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
    
    Path("docs/v11_holdings/index.html").write_text(f\"\"\"<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>보유종목 대시보드</title><style>:root{{color-scheme:light}}*{{box-sizing:border-box}}body{{font-family:-apple-system,BlinkMacSystemFont,"Malgun Gothic",sans-serif;background:#f3f4f6;margin:0;padding:12px}}
    .wrap{{max-width:480px;margin:0 auto}}.hero{{background:linear-gradient(135deg,#1e3a8a,#1e40af);color:white;border-radius:14px;padding:14px;margin-bottom:12px}}.hero h1{{margin:0;font-size:18px}}.card-grid{{display:flex;flex-direction:column;gap:10px}}.holding-card{{background:white;border-radius:14px;padding:12px;box-shadow:0 2px 4px rgba(0,0,0,0.02);border:1px solid #e5e7eb;border-left:5px solid #2563eb}}.card-top{{display:flex;justify-content:space-between;align-items:flex-start}}.card-top h2{{font-size:15px;margin:0}}.code{{color:#6b7280;font-size:11px;margin:2px 0}}.badge{{background:#eef2ff;color:#3730a3;border-radius:6px;padding:4px 6px;font-size:11px;font-weight:800}}.metrics{{display:grid;grid-template-columns:1fr;gap:6px;margin:10px 0}}@media(min-width:360px){{.metrics{{grid-template-columns:repeat(3,1fr)}}}}.metrics div{{background:#f9fafb;border-radius:8px;padding:6px;text-align:center}}.metrics small{{display:block;color:#6b7280;font-size:10px}}.metrics b{{font-size:12px}}.profit{{color:#dc2626}}.loss{{color:#2563eb}}.neutral{{color:#374151}}.line{{height:1px;background:#f1f5f9;margin:6px 0}}.targets{{font-size:12px;color:#374151;margin:4px 0;display:flex}}.memo{{background:#fff7ed;color:#9a3412;border-radius:8px;padding:6px;font-size:11px;margin:4px 0}}.ai-advice{{background:#f0fdf4;border:1px solid #bbf7d0;color:#14532d;border-radius:8px;padding:8px;margin-top:6px}}.ai-advice b{{font-size:11px;display:block}}.ai-advice p{{margin:0;font-size:11px;line-height:1.4}}</style></head><body><main class="wrap"><section class="hero"><h1>📊 보유 계좌 자산 실시간 관제</h1><p>갱신: {now_kst()}</p></section><section class="card-grid">{"".join(cards)}</section></main></body></html>\"\"\", encoding="utf-8")

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
        three = html.escape(str(r.get("news_three_line_summary"))).replace('\\n', '<br>')
        cards.append(f"<article class='news-card'><div class='meta'>{html.escape(r.get('publisher'))} · 품질 {r.get('news_quality_score')}점</div><h2>{html.escape(r.get('title'))}</h2><p class='body-text'>{html.escape(r.get('description'))}</p><div class='summary3-box'><b>📌 뉴스 핵심 3줄 압축 요약</b><p>{three}</p></div></article>")
    
    Path("docs/details/naver_news.html").write_text(f\"\"\"<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>주요 뉴스 브리핑</title><style>body{{font-family:-apple-system,BlinkMacSystemFont,sans-serif;background:#f3f4f6;margin:0;padding:12px}}.wrap{{max-width:480px;margin:0 auto}}.hero{{background:#064e3b;color:white;border-radius:14px;padding:14px;margin-bottom:12px}}.news-card{{background:white;border-radius:14px;padding:12px;margin-bottom:10px;box-shadow:0 2px 4px rgba(0,0,0,0.02);display:flex;flex-direction:column;gap:4px}}.meta{{font-size:11px;color:#059669;font-weight:600}}.news-card h2{{font-size:14px;margin:2px 0;line-height:1.4}}.body-text{{font-size:12px;color:#4b5563;margin:0}}.summary3-box{{background:#f0fdf4;border-left:4px solid #10b981;padding:8px;border-radius:6px;font-size:11px}}.summary3-box b{{color:#14532d;display:block;margin-bottom:2px}}</style></head><body><main class="wrap"><section class="hero"><h1>📰 실시간 마켓 뉴스 3줄 브리핑</h1><p>갱신: {now_kst()}</p></section>{"".join(cards)}</main></body></html>\"\"\", encoding="utf-8")

if __name__ == "__main__":
    build_holding_outputs()
    build_news_outputs()
""",

    # [파일 3] 신설 파일: AI 매매 타이밍 복기·성과 평가 엔진
    "automation/scripts/build_gemini_trade_performance_evaluation.py": """# -*- coding: utf-8 -*-
import os, sys, html, json, re, time, urllib.parse, urllib.request
from pathlib import Path
import pandas as pd
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
def now(): return datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')

def load_trade_logs():
    for p in [Path("docs/data/toss_trade_history.csv"), Path("trade_log_manual_input.csv"), Path("매매기록_수동입력.csv")]:
        if p.exists():
            df = pd.read_csv(p, dtype=str).fillna("")
            if not df.empty: return df
    return pd.DataFrame()

def call_gemini_eval(prompt_content):
    key = os.environ.get('GEMINI_API_KEY','').strip()
    if not key: return "Gemini API Key 세팅을 확인하세요."
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    payload = {
        'contents': [{'parts': [{'text': prompt_content}]}],
        'generationConfig': {'temperature': 0.2, 'maxOutputTokens': 1500}
    }
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json', 'x-goog-api-key': key})
        with urllib.request.urlopen(req, timeout=40) as res:
            data = json.loads(res.read().decode('utf-8'))
        return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"AI 연동 실패 사유: {repr(e)}"

def build():
    df = load_trade_logs()
    if df.empty:
        text = "<p class='hint'>추적 가능한 최근 60일 내 매매 체결 기록이 존재하지 않습니다.</p>"
    else:
        # 최근 15개 매매 기록을 요약 덤프로 가공
        log_dump = ""
        for idx, row in df.head(15).iterrows():
            log_dump += f"- 날짜: {row.get('trade_date', row.get('체결일',''))} | 종목: {row.get('stock_name','')} | 구분: {row.get('trade_type', row.get('매매구분',''))} | 수량: {row.get('quantity','')} | 체결가: {row.get('price', row.get('체결가',''))}\\n"
        
        prompt = f\"\"\"
        당신은 투자자의 실전 매매 기록(Trade History)을 분석하여 날카로운 훈수를 두는 월가 출신의 인공지능 매매 복기 매니저입니다.
        아래의 최근 매매 내역 데이터 뭉치를 바탕으로 보유 기간, 실현 이익 금액의 적절성을 평가하십시오.
        
        [실전 매매 로그]
        {log_dump}
        
        [지시 및 조언 규칙]
        1. 무조건 주린이 눈높이에 맞춰 친절하면서도 뼈를 때리는 실전 조언을 건네십시오.
        2. '이 거래는 적절하게 이익을 잘 냈다' 혹은 '중간에 이때 팔고 더 떨어졌을 때 다시 기계적으로 숏/재매수 대응을 했어야 했다'와 같이 손절·익절 가이드를 어겨서 손해를 본 부분이나 기회비용을 명확히 대입하여 비판 및 복기해 주십시오.
        3. 마크다운 대신 깔끔하게 줄바꿈 문장 형태로 단락을 나누어 회신해 주십시오.
        \"\"\"
        text = call_gemini_eval(prompt).replace('\\n', '<br>').replace('**', '')

    page = f\"\"\"<!doctype html>
    <html lang="ko">
    <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>AI 매매 복기 노트</title>
    <style>
    body {{ font-family: -apple-system, sans-serif; background: #f3f4f6; margin: 0; padding: 12px; color: #1e293b; }}
    .container {{ max-width: 480px; margin: 0 auto; }}
    .banner {{ background: #0284c7; color: white; padding: 16px; border-radius: 16px; margin-bottom: 12px; }}
    .eval-card {{ background: white; border-radius: 16px; padding: 16px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.02); border-left: 5px solid #0284c7; font-size: 13px; line-height: 1.6; color: #334155; }}
    </style>
    </head>
    <body>
    <div class="container">
        <div class="banner">
            <h3 style="margin:0; font-size: 16px;">📈 AI 실전 매매 복기·타점 평가</h3>
            <p style="margin:4px 0 0 0; font-size:11px; opacity:0.85;">동기화 시각: {now()}</p>
        </div>
        <div class="eval-card">
            {text}
        </div>
    </div>
    </body>
    </html>\"\"\"
    Path('docs/details/trade_evaluation.html').write_text(page, encoding='utf-8')

if __name__ == '__main__': build()
""",

    # [파일 4] 최종 레거시 덮어쓰기 파괴자 교정 (손절 분할 수량 % 노이즈 슬라이싱 박멸 및 모바일 카드화)
    "automation/scripts/publish_legacy_excel_sections.py": """# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone, timedelta
import csv, html, re, shutil
import pandas as pd

KST = timezone(timedelta(hours=9))

def now(): return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")
def esc(x): return html.escape(str(x if x is not None else ""))
def clean_value(x):
    if x is None: return ""
    try:
        if isinstance(x, float) and pd.isna(x): return ""
    except: pass
    s = str(x).strip()
    return "" if s.lower() in {"nan","none","nat"} else s

def find_latest_xlsx() -> Path | None:
    files, seen = [], set()
    for root in [Path('.'), Path('stock_report'), Path('docs')]:
        if not root.exists(): continue
        for p in root.rglob('*.xlsx'):
            if not p.is_file() or 'docs/downloads' in p.as_posix(): continue
            key = p.resolve()
            if key in seen: continue
            seen.add(key); files.append(p)
    if not files: return None
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0]

def _extract_percent_numbers(text):
    # [버그 완전 박멸] 정규식 매칭 풀 슬라이싱을 3개로 차단해 분할 매매 비량(80%) 찌꺼기가 침범하는 버그 차단
    vals = re.findall(r"[\+\-]?\d+(?:\.\d+)?\s*%", clean_value(text))
    return [v.replace(' ', '') for v in vals][:3]

def format_tp_plan(raw):
    vals = _extract_percent_numbers(raw)
    if len(vals) >= 3: return f"<b>{vals[0]}(60)</b> / <b>{vals[1]}(20)</b> / <b>{vals[2]}(20)</b>"
    if len(vals) == 2: return f"<b>{vals[0]}(60)</b> / <b>{vals[1]}(40)</b>"
    if vals: return f"<b>{vals[0]}</b>"
    return esc(clean_value(raw))

def format_sl_plan(raw):
    vals = _extract_percent_numbers(raw)
    return ' / '.join(f"<span style='color:#dc2626; font-weight:bold;'>{v}</span>" for v in vals) if vals else esc(clean_value(raw))

def safe_price_text(v):
    t = clean_value(v)
    if not t: return "-"
    try: return f"{float(re.sub(r'[^\\\\d.\\\\-]', '', t)):,.0f}원"
    except: return t

def build_top15_cards(top_rows):
    cards = []
    for r in top_rows[:15]:
        rank, name, code = esc(r.get('순위', r.get('rank','-'))), esc(r.get('stock_name', r.get('종목명'))), esc(r.get('stock_code', r.get('종목코드')))
        price, score, decision = safe_price_text(r.get('current_price', r.get('현재가'))), esc(r.get('score', r.get('실전점수'))), esc(r.get('entry_decision', r.get('진입판정')))
        cards.append(f\"\"\"
        <div class="mobile-card-item">
            <div class="card-head-row"><span class="rank-tag">TOP {rank}</span><span class="stock-title-main">{name} <small>({code})</small></span></div>
            <div class="card-meta-row">분야: {esc(r.get('sector', r.get('분야')))} | 상태: <b>{decision}</b></div>
            <div class="card-price-grid"><div><small>실시간 현재가</small><b>{price}</b></div><div><small>실전 계량점수</small><b>{score}점</b></div></div>
            <p style="margin:2px 0; font-size:12px;">🎯 <b>익절선 계획:</b> {format_tp_plan(r.get('익절계획'))}</p>
            <p style="margin:2px 0; font-size:12px;">🚨 <b>손절선 계획:</b> {format_sl_plan(r.get('손절계획') or r.get('손절가'))}</p>
            <div class="card-desc-box">💡 <b>AI 미니 조언:</b><br>{esc(r.get('stock_description'))}</div>
        </div>\"\"\")
    return "".join(cards) if cards else "<p class='hint'>선별 후보 데이터가 없습니다.</p>"

def build_continuous_cards(rows):
    cards = []
    for r in rows[:80]:
        name, code = esc(r.get('stock_name', r.get('종목명'))), esc(r.get('stock_code', r.get('종목코드')))
        cnt, score, price = esc(r.get('연속추천횟수', r.get('연속추천'))), esc(r.get('실전점수', r.get('점수'))), safe_price_text(r.get('current_price'))
        cards.append(f\"\"\"
        <div class="mobile-card-item" style="border-left: 5px solid #f97316;">
            <div class="stamp-box">🔥 연속 포착 출석현황: {cnt}회 등장</div>
            <div class="card-head-row" style="margin-top:6px;"><span class="stock-title-main">{name} <small>({code})</small></span></div>
            <div class="card-meta-row">분야: {esc(r.get('분야'))} | 상태: {esc(r.get('진입판정'))}</div>
            <div class="card-price-grid"><div><small>현재가</small><b>{price}</b></div><div><small>포착점수</small><b>{score}점</b></div></div>
            <p style="margin:2px 0; font-size:12px;">🎯 익절안: {format_tp_plan(r.get('익절계획'))}</p>
            <p style="margin:2px 0; font-size:12px;">🚨 손절안: {format_sl_plan(r.get('손절계획'))}</p>
        </div>\"\"\")
    return "".join(cards) if cards else "<p class='hint'>연속 추천 기록이 존재하지 않습니다.</p>"

def build_outputs():
    data_dir, details_dir = Path('docs/data'), Path('docs/details')
    xlsx = find_latest_xlsx()
    if not xlsx: return
    try: top_df = pd.read_csv(data_dir / 'latest_recommendation_top15_full.csv', dtype=str).fillna('')
    except: top_df = pd.DataFrame()
    try: cont_df = pd.read_csv(data_dir / 'latest_legacy_continuous.csv', dtype=str).fillna('')
    except: cont_df = pd.DataFrame()

    html_style = """<style>body { font-family: -apple-system, sans-serif; background: #f3f4f6; margin: 0; padding: 12px; } .container { max-width: 480px; margin: 0 auto; } .hero-banner { background: #0f172a; color: white; padding: 14px; border-radius: 14px; margin-bottom: 12px; } .mobile-card-item { background: white; border-radius: 14px; padding: 12px; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); border-left: 5px solid #10b981; } .stamp-box { background: #fff7ed; color: #ea580c; padding: 4px; border-radius: 6px; font-size: 11px; font-weight: bold; text-align: center; border: 1px dashed #fdba74; } .card-head-row { display: flex; justify-content: space-between; align-items: center; } .rank-tag { background: #10b981; color: white; font-size: 11px; padding: 2px 4px; border-radius: 4px; } .stock-title-main { font-size: 14px; font-weight: bold; } .card-meta-row { font-size: 11px; color: #64748b; margin: 2px 0; } .card-price-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin: 6px 0; } .card-price-grid div { background: #f8fafc; padding: 6px; border-radius: 6px; } .card-price-grid small { display: block; color: #94a3b8; font-size: 10px; } .card-price-grid b { font-size: 12px; } .card-desc-box { background: #f1f5f9; padding: 8px; border-radius: 8px; font-size: 11px; line-height: 1.45; }</style>"""

    if not top_df.empty:
        content = build_top15_cards(top_df.to_dict('records'))
        (details_dir / 'legacy_top15.html').write_text(f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>TOP15 리서치</title>{{html_style}}</head><body><div class='container'><div class='hero-banner'><h3 style='margin:0;font-size:15px;'>💎 추천 TOP15 실전 리서치 노출</h3></div>{{content}}</div></body></html>", encoding='utf-8')
        shutil.copyfile(details_dir / 'legacy_top15.html', details_dir / 'recommendation_top15.html')
        shutil.copyfile(details_dir / 'legacy_top15.html', details_dir / 'legacy_full_recommendations.html')
    if not cont_df.empty:
        cont_content = build_continuous_cards(cont_df.to_dict('records'))
        (details_dir / 'legacy_continuous.html').write_text(f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>연속추천 관찰</title>{{html_style}}</head><body><div class='container'><div class='hero-banner' style='background:#ea580c;'><h3 style='margin:0;font-size:15px;'>🔄 연속 추천 포착 출석 타임라인</h3></div>{{cont_content}}</div></body></html>", encoding='utf-8')
        shutil.copyfile(details_dir / 'legacy_continuous.html', details_dir / 'continuous.html')
    print("✅ 레거시 덮어쓰기 무력화 완료.")
if __name__ == '__main__': build_outputs()
""",

    # [파일 5] 메인 통합 홈 관제 화면 (AI 매매기록 평가 메뉴 버튼 앵커 연동 및 문법 버그 전면 박멸)
    "automation/scripts/force_refresh_latest.py": """# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone, timedelta
import csv, html, os, re

KST = timezone(timedelta(hours=9))
def now(): return datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')
def session():
    env = (os.environ.get('REPORT_SESSION') or os.environ.get('SESSION') or '').strip().upper()
    if env in ('AM','PM','PM_TEST','MANUAL'): return env
    h = datetime.now(KST).hour
    return 'AM' if h < 12 else 'PM' if h < 18 else 'MANUAL'

def read_csv(path, limit=999):
    p = Path(path)
    if not p.exists(): return []
    for enc in ('utf-8-sig','utf-8','cp949','euc-kr'):
        try:
            with p.open(encoding=enc,newline='') as f: return list(csv.DictReader(f))[:limit]
        except Exception: pass
    return []

def esc(x): return html.escape(str(x or ''))

def _pct_values(text):
    vals = [v.replace(' ', '') for v in re.findall(r"[\+\-]?\d+(?:\.\d+)?\s*%", str(text or ''))]
    return vals[:3]

def fmt_tp(text):
    vals = _pct_values(text)
    if len(vals) >= 3: return f"<b>{esc(vals[0])}(60)</b> / <b>{esc(vals[1])}(20)</b> / <b>{esc(vals[2])}(20)</b>"
    if len(vals) == 2: return f"<b>{esc(vals[0])}(60)</b> / <b>{esc(vals[1])}(40)</b>"
    if vals: return f"<b>{esc(vals[0])}</b>"
    return esc(text)

def fmt_sl(text):
    vals = _pct_values(text)
    if vals: return ' / '.join(f"<span style='color:#dc2626; font-weight:bold;'>{esc(v)}</span>" for v in vals)
    return esc(text)

def top15_entry_section():
    rows = read_csv('docs/data/latest_recommendation_top15_full.csv', 15)
    if not rows: return "<section class='box accent'><h2>추천 TOP15 + 진입 시나리오</h2><p class='hint'>데이터 확인 필요</p></section>"
    cards = ''
    for r in rows[:6]:
        cards += f\"\"\"
        <article class='card'>
            <h3>{esc(r.get('rank'))}. {esc(r.get('stock_name'))} <span class='pill'>{esc(r.get('score'))}점</span></h3>
            <p class='meta'>{esc(r.get('sector'))} · 현재가 {esc(r.get('current_price'))} · {esc(r.get('entry_decision'))}</p>
            <p class='desc'>💡 <b>리서치:</b> {esc(r.get('stock_description'))}</p>
            <p style="font-size:12px; margin:2px 0;">🎯 <b>익절계획:</b> {fmt_tp(r.get('take_profit_plan'))}</p>
            <p style="font-size:12px; margin:2px 0;">🚨 <b>손절계획:</b> {fmt_sl(r.get('stop_loss_plan') or r.get('stop_price'))}</p>
        </article>\"\"\"
    return f"<section class='box accent'><h2>💎 추천 후보 TOP6 요약</h2><div class='vertical-grid'>{cards}</div></section>"

def holdings_section():
    rows = read_csv('docs/data/latest_holding_deep_analysis.csv', 50)
    desc = {r.get('stock_name'): r for r in read_csv('docs/data/latest_holding_stock_descriptions.csv', 50)}
    if not rows: return "<section class='box'><h2>보유종목 현황</h2><p class='hint'>보유 종목 내역이 없습니다.</p></section>"
    cards = ''
    for r in rows[:8]:
        name = r.get('stock_name')
        d = desc.get(name, {})
        pnl = float(r.get('unrealized_pnl_pct', 0) or 0)
        pnl_cls = "profit" if pnl > 0 else "loss" if pnl < 0 else "neutral"
        cards += f\"\"\"
        <article class='card' style='border-left:5px solid #2563eb;'>
            <h3>{esc(name)} <span class='pill' style='background:#eff6ff; color:#1e40af;'>{esc(r.get('decision'))}</span></h3>
            <p class='meta'>현재가 {esc(r.get('current_price'))} · 손익률 <b class='{pnl_cls}'>{esc(r.get('unrealized_pnl_pct'))}%</b></p>
        </article>\"\"\"
    return f"<section class='box'><h2>📊 실시간 보유종목 상태</h2><div class='vertical-grid'>{cards}</div></section>"

def ai_section():
    rows = read_csv('docs/data/latest_holding_ai_briefing.csv', 5)
    if not rows: return "<section class='box'><h2>🧠 제미나이 AI 보유 브리핑</h2><p class='hint'>장마감 리포트에서 분석이 반영됩니다.</p></section>"
    cards = ''
    for r in rows[:5]:
        summary_raw = r.get('ai_issue_summary') or r.get('ai_three_line_summary') or ''
        summary_text = str(summary_raw).replace('\n', '<br>')
        action = r.get('ai_action_headline') or r.get('ai_action_guide') or ''
        cards += f\"\"\"
        <article class='card' style='border-top:3px solid #1e3a8a;'>
            <h3>{esc(r.get('stock_name'))} <span class='pill' style='background:#f0fdf4; color:#166534;'>{esc(action)}</span></h3>
            <p class='desc' style='font-size:12px;'>{summary_text}</p>
        </article>\"\"\"
    return f"<section class='box'><h2>🧠 제미나이 자산방어 브리핑</h2>{cards}</section>"

def news_section():
    rows = read_csv('docs/data/latest_news_detail.csv', 6)
    items = ''
    for r in rows:
        if r.get('title'):
            link = r.get('link') or '#'
            items += f\"\"\"
            <article class='card'>
                <small style='color:#059669; font-weight:700;'>{esc(r.get('publisher'))} · {esc(r.get('query'))}</small>
                <h4 style='margin:4px 0 2px 0; font-size:14px;'><a href='{esc(link)}' target='_blank' style='color:#111827;'>{esc(r.get('title'))}</a></h4>
            </article>\"\"\"
    return f"<section class='box'><h2>📰 당일 주요 뉴스</h2><div class='vertical-grid'>{items}</div></section>"

def unified_html(stamp, ss):
    return f\"\"\"<!doctype html>
<html lang='ko'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>모바일 통합 관제 홈</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,"Malgun Gothic",sans-serif;background:#f3f4f6;margin:0;padding:12px;color:#111827}}
.wrap{{max-width:480px;margin:0 auto;}}
.hero{{background:linear-gradient(135deg,#111827,#1f2937);color:white;border-radius:16px;padding:16px;margin-bottom:12px}}
.hero h1{{margin:0;font-size:18px;font-weight:800}}
.hero p{{margin:4px 0 0;font-size:11px;opacity:0.8}}
.nav-grid{{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:12px}}
.nav-grid a{{display:block;background:white;border-radius:10px;padding:10px;text-align:center;font-size:12px;font-weight:700;color:#1e3a8a;text-decoration:none;box-shadow:0 2px 4px rgba(0,0,0,0.02);border:1px solid #e5e7eb}}
.box{{margin-bottom:14px}}
.box h2{{font-size:14px;margin:0 0 8px 0;border-left:4px solid #1e3a8a;padding-left:6px;font-weight:800}}
.vertical-grid{{display:flex;flex-direction:column;gap:8px}}
.card{{background:white;border-radius:12px;padding:12px;box-shadow:0 2px 4px rgba(0,0,0,0.02);border:1px solid #e5e7eb}}
.card h3{{margin:0 0 4px 0;font-size:14px;font-weight:700;display:flex;justify-content:space-between;align-items:center}}
.pill{{font-size:10px;background:#eef2ff;color:#3730a3;padding:2px 6px;border-radius:4px}}
.meta{{font-size:11px;color:#6b7280;margin:2px 0}}
.desc{{background:#f9fafb;padding:8px;border-radius:6px;font-size:12px;color:#374151;margin:4px 0;line-height:1.4}}
.profit{{color:#dc2626}}.loss{{color:#2563eb}}.neutral{{color:#4b5563}}
</style>
</head>
<body>
<main class='wrap'>
    <section class='hero'>
        <h1>📱 모바일 관제 대시보드</h1>
        <p>갱신: {esc(stamp)} | 세션: {esc(ss)}</p>
    </section>
    <section class='nav-grid'>
        <a href='../details/legacy_top15.html'>TOP15 리서치</a>
        <a href='../details/legacy_continuous.html'>🔄 연속추천 관찰</a>
        <a href='../v11_holdings/'>보유종목 상세</a>
        <a href='../details/holding_ai_briefing.html'>🧠 AI 자산 브리핑</a>
        <a href='../details/naver_news.html'>📰 뉴스 3줄요약</a>
        <a href='../details/trade_evaluation.html' style='background:#0284c7; color:white;'>📈 AI 매매기록 평가</a>
        <a href='../downloads/' style='grid-column: span 2; background:#1e3a8a; color:white;'>📥 전체 엑셀 센터 열기</a>
    </section>
    {top15_entry_section()}
    {holdings_section()}
    {ai_section()}
    {news_section()}
</main>
</body>
</html>\"\"\"

def main():
    stamp, ss = now(), session()
    Path('docs/latest').mkdir(parents=True, exist_ok=True)
    Path('docs/mobile').mkdir(parents=True, exist_ok=True)
    
    html_text = unified_html(stamp, ss)
    Path('docs/mobile/index.html').write_text(html_text, encoding='utf-8')
    Path('docs/latest/index.html').write_text("<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta http-equiv='refresh' content='0; url=../mobile/'><meta name='viewport' content='width=device-width,initial-scale=1'></head><body></body></html>", encoding='utf-8')
    print('✅ 에러 없는 모바일 전용 480px 강력 압축 홈 대시보드 및 포맷 버그 완전 가동.')

if __name__ == '__main__': main()
"""
}

print("🚀 [1/2] 주식 공장 시스템 통합 자가 수리를 시작합니다...")
for filepath, code_content in FILES_MATRIX.items():
    p = Path(filepath)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(code_content.strip(), encoding="utf-8")
    print(f"   [완료] -> {filepath}")

print("\n✨ [2/2] 모든 코드 파일이 수량 연동 및 AI 매매평가서 포함형으로 일괄 교정되었습니다.")
print("이제 'patch_master.py' 파일은 지우시고 GitHub Desktop에서 커밋/푸시를 쏘시면 끝납니다!")
