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
    client = TossInvestClient()
    status_path = out_dir / "toss_api_status.csv"
    out_path = out_dir / "toss_holdings_snapshot.csv"

    if not client.configured():
        pd.DataFrame([status_row("SKIPPED", "Toss API credentials are missing")]).to_csv(status_path, index=False, encoding="utf-8-sig")
        pd.DataFrame().to_csv(out_path, index=False, encoding="utf-8-sig")
        print("⚠️ Toss holdings skipped: credentials missing")
        return

    try:
        data, endpoint = client.get_holdings()
        records = flatten_records(data)
        rows = []
        for r in records:
            name = pick(r, ["stockName", "stock_name", "name", "korName", "instrumentName", "symbolName", "종목명"])
            code = normalize_code(pick(r, ["stockCode", "stock_code", "code", "symbol", "ticker", "instrumentId", "종목코드"]))
            qty = pick(r, ["quantity", "qty", "holdingQuantity", "balanceQuantity", "보유수량", "수량"])
            avg = pick(r, ["averagePrice", "avgPrice", "avg_price", "purchaseAveragePrice", "평균단가", "매입단가"])
            cur = pick(r, ["currentPrice", "price", "lastPrice", "marketPrice", "현재가"])
            value = pick(r, ["evaluationAmount", "marketValue", "value", "평가금액"])
            pnl = pick(r, ["profitLoss", "unrealizedPnl", "valuationProfitLoss", "평가손익"])
            pnl_pct = pick(r, ["profitLossRate", "unrealizedPnlPct", "returnRate", "손익률"])
            if not name and not code:
                continue
            rows.append({
                "stock_name": name,
                "stock_code": code,
                "quantity": to_num(qty),
                "avg_price": to_num(avg),
                "current_price": to_num(cur),
                "market_value": to_num(value),
                "unrealized_pnl": to_num(pnl),
                "unrealized_pnl_pct": to_num(pnl_pct),
                "source": "toss_api",
                "endpoint": endpoint,
            })
        pd.DataFrame(rows).to_csv(out_path, index=False, encoding="utf-8-sig")
        pd.DataFrame([status_row("OK", f"holdings rows={len(rows)}", endpoint)]).to_csv(status_path, index=False, encoding="utf-8-sig")
        print(f"✅ Toss holdings snapshot rows={len(rows)}")
    except Exception as e:
        pd.DataFrame([status_row("ERROR", repr(e))]).to_csv(status_path, index=False, encoding="utf-8-sig")
        pd.DataFrame().to_csv(out_path, index=False, encoding="utf-8-sig")
        print(f"⚠️ Toss holdings snapshot failed: {e!r}")


if __name__ == "__main__":
    main()
