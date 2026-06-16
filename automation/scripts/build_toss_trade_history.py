#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
import pandas as pd

from toss_api_client import TossInvestClient, flatten_records, pick, normalize_code, status_row


def to_num(x):
    text = str(x or "").replace(",", "").replace("%", "").strip()
    try:
        return float(text)
    except Exception:
        return ""


def main() -> None:
    out_dir = Path("docs/data")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "toss_trade_history.csv"
    status_path = out_dir / "toss_trade_status.csv"
    client = TossInvestClient()

    if not client.configured():
        pd.DataFrame([status_row("SKIPPED", "Toss API credentials are missing")]).to_csv(status_path, index=False, encoding="utf-8-sig")
        pd.DataFrame().to_csv(out_path, index=False, encoding="utf-8-sig")
        print("⚠️ Toss trade history skipped: credentials missing")
        return

    try:
        data, endpoint = client.get_order_history()
        records = flatten_records(data)
        rows = []
        for r in records:
            name = pick(r, ["stockName", "stock_name", "name", "종목명"])
            code = normalize_code(pick(r, ["stockCode", "stock_code", "code", "symbol", "ticker", "종목코드"]))
            side = pick(r, ["side", "orderSide", "tradeType", "buySellType", "매매구분"])
            qty = pick(r, ["quantity", "executedQuantity", "filledQuantity", "qty", "수량"])
            price = pick(r, ["price", "executionPrice", "filledPrice", "체결가"])
            date = pick(r, ["date", "tradeDate", "executionDate", "executedAt", "createdAt", "체결일"])
            if not name and not code:
                continue
            rows.append({
                "trade_date": date,
                "trade_type": side,
                "stock_name": name,
                "stock_code": code,
                "quantity": to_num(qty),
                "price": to_num(price),
                "source": "toss_api",
                "endpoint": endpoint,
            })
        pd.DataFrame(rows).to_csv(out_path, index=False, encoding="utf-8-sig")
        pd.DataFrame([status_row("OK", f"trade rows={len(rows)}", endpoint)]).to_csv(status_path, index=False, encoding="utf-8-sig")
        print(f"✅ Toss trade history rows={len(rows)}")
    except Exception as e:
        pd.DataFrame([status_row("ERROR", repr(e))]).to_csv(status_path, index=False, encoding="utf-8-sig")
        pd.DataFrame().to_csv(out_path, index=False, encoding="utf-8-sig")
        print(f"⚠️ Toss trade history failed: {e!r}")


if __name__ == "__main__":
    main()
