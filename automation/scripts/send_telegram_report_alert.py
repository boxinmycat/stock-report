#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone, timedelta
import csv
import os
import urllib.parse
import urllib.request
import urllib.error

KST = timezone(timedelta(hours=9))


def now_kst() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")


def read_csv_dicts(path: Path, limit: int = 50) -> list[dict]:
    if not path.exists():
        return []
    for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
        try:
            with path.open("r", encoding=enc, newline="") as f:
                return list(csv.DictReader(f))[:limit]
        except Exception:
            pass
    return []


def pick(row: dict, names: list[str]) -> str:
    lower = {str(k).strip().lower(): k for k in row.keys()}
    for name in names:
        key = name.strip().lower()
        if key in lower:
            return str(row.get(lower[key], "")).strip()
    for k, v in row.items():
        kk = str(k).strip().lower()
        for name in names:
            if name.strip().lower() in kk:
                return str(v).strip()
    return ""


def read_status() -> dict:
    rows = read_csv_dicts(Path("docs/data/latest_publish_status.csv"), limit=20)
    out = {}
    for row in rows:
        key = pick(row, ["key"])
        val = pick(row, ["value"])
        if key:
            out[key] = val
    return out


def detect_session() -> str:
    status = read_status()
    session = (status.get("session") or os.environ.get("REPORT_SESSION") or os.environ.get("SESSION") or "").strip().upper()
    if session in {"AM", "PM", "MANUAL"}:
        return session
    hour = datetime.now(KST).hour
    if hour < 12:
        return "AM"
    if hour < 18:
        return "PM"
    return "MANUAL"


def top_candidates_text() -> str:
    rows = read_csv_dicts(Path("docs/data/latest_candidates.csv"), limit=5)
    if not rows:
        return "추천후보: 데이터 확인 필요"
    lines = ["추천후보 TOP"]
    for i, row in enumerate(rows[:5], start=1):
        name = pick(row, ["stock_name", "종목명", "name"])
        score = pick(row, ["score", "점수", "추천점수"])
        sector = pick(row, ["sector", "분야", "테마"])
        if not name:
            continue
        line = f"{i}. {name}"
        if score:
            line += f" / 점수 {score}"
        if sector:
            line += f" / {sector}"
        lines.append(line)
    return "\n".join(lines) if len(lines) > 1 else "추천후보: 데이터 확인 필요"


def holdings_text() -> str:
    rows = read_csv_dicts(Path("docs/data/latest_holding_deep_analysis.csv"), limit=100)
    if not rows:
        return "보유종목: 심화분석 데이터 확인 필요"
    counts = {}
    alerts = []
    for row in rows:
        decision = pick(row, ["decision", "판단"]) or "UNKNOWN"
        counts[decision] = counts.get(decision, 0) + 1
        if decision in {"TAKE_PROFIT", "TAKE_PROFIT_1", "STOP_WATCH", "PRICE_NOT_MATCHED"}:
            name = pick(row, ["stock_name", "종목명", "name"])
            pnl = pick(row, ["unrealized_pnl_pct", "손익률"])
            src = pick(row, ["current_price_source", "매칭상태"])
            if name:
                s = f"{name}({decision}"
                if pnl:
                    s += f", {pnl}%"
                if src:
                    s += f", {src}"
                s += ")"
                alerts.append(s)
    text = "보유종목 판단: " + ", ".join(f"{k} {v}개" for k, v in sorted(counts.items()))
    if alerts:
        text += "\n주의/확인: " + " / ".join(alerts[:5])
    return text


def strategy_text() -> str:
    rows = read_csv_dicts(Path("docs/data/latest_strategy_validation_summary.csv"), limit=5)
    if not rows:
        return "전략검증: 검증중"
    lines = ["전략검증 요약"]
    for row in rows[:3]:
        strategy = pick(row, ["strategy", "전략", "model"])
        verdict = pick(row, ["verdict", "판정", "status"])
        avg = pick(row, ["avg_return", "평균수익률", "return"])
        if strategy or verdict or avg:
            parts = [strategy or "전략"]
            if verdict:
                parts.append(verdict)
            if avg:
                parts.append(f"평균 {avg}")
            lines.append(" / ".join(parts))
    return "\n".join(lines) if len(lines) > 1 else "전략검증: 검증중"


def build_message() -> str:
    status = read_status()
    session = detect_session()
    published_at = status.get("published_at") or now_kst()
    title = "[장전 리포트 완료]" if session == "AM" else "[장마감 리포트 완료]" if session == "PM" else "[주식 리포트 완료]"
    return f"""{title}

생성시각: {published_at}
세션: {session}

{top_candidates_text()}

{holdings_text()}

{strategy_text()}

모바일 홈:
https://boxinmycat.github.io/stock-report/mobile/

최신 리포트:
https://boxinmycat.github.io/stock-report/latest/

보유종목:
https://boxinmycat.github.io/stock-report/v11_holdings/

전략검증:
https://boxinmycat.github.io/stock-report/strategy/
"""


def send_telegram(text: str) -> int:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    print("TELEGRAM_BOT_TOKEN:", "OK" if token else "MISSING")
    print("TELEGRAM_CHAT_ID:", "OK" if chat_id else "MISSING")
    if not token or not chat_id:
        print("⚠️ Telegram secrets missing. Skip alert.")
        return 0
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": "true",
    }).encode("utf-8")
    try:
        with urllib.request.urlopen(url, data=data, timeout=15) as res:
            body = res.read().decode("utf-8", errors="ignore")
            print("✅ Telegram alert sent")
            print(body[:500])
            return 0
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        print("❌ Telegram HTTP error:", e.code)
        print(body[:1000])
        return 1
    except Exception as e:
        print("❌ Telegram alert error:", repr(e))
        return 1


def main() -> int:
    msg = build_message()
    print("Telegram message preview:")
    print(msg[:1500])
    return send_telegram(msg)


if __name__ == "__main__":
    raise SystemExit(main())
