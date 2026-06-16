#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
import pandas as pd

from toss_api_client import TossInvestClient, flatten_records, pick, normalize_code, status_row


def read_csv(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return pd.read_csv(p, dtype=str, encoding=enc).fillna("")
        except Exception:
            pass
    return pd.DataFrame()


def to_num(x):
    text = str(x or "").replace(",", "").replace("%", "").strip()
    try:
        return float(text)
    except Exception:
        return ""


def symbols_from_inputs() -> list[dict]:
    out = []
    for path in ["docs/data/toss_holdings_snapshot.csv", "holdings_manual_input.csv", "보유종목_수동입력.csv", "TOSS_수동후보.csv"]:
        df = read_csv(path)
        if df.empty:
            continue
        for _, r in df.iterrows():
            name = r.get("stock_name") or r.get("종목명") or r.get("name") or ""
            code = normalize_code(r.get("stock_code") or r.get("종목코드") or r.get("code") or r.get("ticker") or "")
            if name or code:
                out.append({"stock_name": name, "stock_code": code})
    seen = set()
    uniq = []
    for r in out:
        key = r["stock_code"] or r["stock_name"]
        if key and key not in seen:
            seen.add(key)
            uniq.append(r)
    return uniq


def main() -> None:
    out_dir = Path("docs/data")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "toss_price_snapshot.csv"
    status_path = out_dir / "toss_price_status.csv"
    client = TossInvestClient()

    if not client.configured():
        pd.DataFrame([status_row("SKIPPED", "Toss API credentials are missing")]).to_csv(status_path, index=False, encoding="utf-8-sig")
        pd.DataFrame().to_csv(out_path, index=False, encoding="utf-8-sig")
        print("⚠️ Toss price skipped: credentials missing")
        return

    rows = []
    errors = []
    for item in symbols_from_inputs():
        code = item["stock_code"]
        if not code:
            continue
        try:
            data, endpoint = client.get_price(code)
            records = flatten_records(data)
            r = records[0] if records else (data if isinstance(data, dict) else {})
            price = pick(r, ["currentPrice", "price", "lastPrice", "tradePrice", "closePrice", "현재가"])
            rows.append({
                "stock_name": item["stock_name"] or pick(r, ["stockName", "name", "korName"]),
                "stock_code": code,
                "current_price": to_num(price),
                "source": "toss_api",
                "endpoint": endpoint,
            })
        except Exception as e:
            errors.append(f"{code}: {e!r}")
            rows.append({
                "stock_name": item["stock_name"],
                "stock_code": code,
                "current_price": "",
                "source": "toss_api_error",
                "endpoint": "",
            })

    pd.DataFrame(rows).to_csv(out_path, index=False, encoding="utf-8-sig")
    status = "OK" if rows else "EMPTY"
    msg = f"price rows={len(rows)} errors={len(errors)}"
    if errors:
        msg += " / " + " | ".join(errors[:5])
    pd.DataFrame([status_row(status, msg)]).to_csv(status_path, index=False, encoding="utf-8-sig")
    print(f"✅ Toss price snapshot rows={len(rows)} errors={len(errors)}")


if __name__ == "__main__":
    main()
