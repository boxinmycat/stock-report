#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone, timedelta
import csv, html

KST = timezone(timedelta(hours=9))

def now():
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")

def read_csv(path):
    p = Path(path)
    if not p.exists(): return []
    for enc in ("utf-8-sig","utf-8","cp949","euc-kr"):
        try:
            with p.open(encoding=enc, newline="") as f:
                return list(csv.DictReader(f))
        except Exception:
            pass
    return []

def kv(rows):
    return {r.get("key",""): r.get("value","") for r in rows}

def esc(x):
    return html.escape(str(x or ""))

def main():
    data = Path("docs/data")
    details = Path("docs/details")
    details.mkdir(parents=True, exist_ok=True)
    sched = kv(read_csv(data/"latest_schedule_diagnostics.csv"))
    prof = read_csv(data/"latest_recommendation_profile_status.csv")
    legacy = read_csv(data/"latest_legacy_sections_status.csv")
    hold = read_csv(data/"latest_holding_ai_briefing.csv")
    price = read_csv(data/"latest_price_validation.csv")
    price_bad = [r for r in price if (r.get('price_validation_status') or '').upper() == 'PRICE_MISMATCH']
    rows = [
        ("event_name", sched.get("event_name")),
        ("event_schedule", sched.get("event_schedule")),
        ("expected_kst", sched.get("expected_kst")),
        ("kst_started_at", sched.get("kst_started_at")),
        ("skip_report", sched.get("skip_report")),
        ("guard_reason", sched.get("guard_reason")),
        ("recommendation_profile_status", prof[0].get("status") if prof else ""),
        ("recommendation_profile_count", prof[0].get("profile_count") if prof else ""),
        ("holding_ai_rows", len(hold)),
        ("legacy_status_rows", len(legacy)),
        ("price_validation_rows", len(price)),
        ("price_mismatch_count", len(price_bad)),
        ("manifest_generated_at", now()),
    ]
    trs = "".join(f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" for k,v in rows)
    page = f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Run Manifest</title><style>body{{margin:0;background:#f6f7fb;color:#111827;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}.wrap{{max-width:980px;margin:auto;padding:20px}}.hero{{background:#111827;color:white;border-radius:22px;padding:22px;margin-bottom:16px}}.card{{background:white;border-radius:18px;padding:16px;box-shadow:0 4px 16px #0001}}table{{border-collapse:collapse;width:100%}}th,td{{border-bottom:1px solid #e5e7eb;padding:10px;text-align:left;font-size:13px}}th{{width:260px;background:#f9fafb}}</style></head><body><main class='wrap'><section class='hero'><h1>Stock Report Run Manifest</h1><p>최종 빌드 상태와 실행 시간 진단 확인용 페이지입니다.</p></section><section class='card'><table>{trs}</table></section></main></body></html>"""
    (details/"run_manifest.html").write_text(page, encoding="utf-8")
    print("✅ run manifest built")

if __name__ == "__main__":
    main()
