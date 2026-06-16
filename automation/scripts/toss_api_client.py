#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Toss Invest Open API read-only client.

Design goals:
- Read-only integration first. No order/create/modify/cancel is implemented.
- Secrets are read only from environment variables.
- Exact endpoint paths can be overridden by env vars.
- If endpoint names differ from assumptions, the client attempts OpenAPI auto-discovery.
- Failures never crash the whole report pipeline; snapshot scripts write status CSVs instead.

Official docs indicate:
- Base API server: https://openapi.tossinvest.com
- OAuth2 Client Credentials Grant for access tokens
- Account/asset/order APIs require X-Tossinvest-Account header in addition to Authorization.
- TOSSINVEST_ACCOUNT is optional. If missing, the client attempts to discover the first account from the accounts API.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import base64
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request


DEFAULT_BASE_URL = "https://openapi.tossinvest.com"
DEFAULT_OPENAPI_URL = "https://openapi.tossinvest.com/openapi-docs/latest/openapi.json"


def env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default or "").strip()


def normalize_code(value: Any) -> str:
    text = str(value or "").strip().upper()
    if not text or text.lower() in {"nan", "none", "null"}:
        return ""
    text = text.replace("=", "").replace('"', "").replace("'", "")
    text = text.replace(",", "").replace(" ", "")
    if re.fullmatch(r"\d+\.0", text):
        text = text[:-2]
    text = re.sub(r"[^0-9A-Z]", "", text)
    if not text:
        return ""
    return text.zfill(6)


def flatten_records(obj: Any) -> list[dict]:
    """Extract likely record lists from an arbitrary API JSON payload."""
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    if not isinstance(obj, dict):
        return []

    # Common direct containers first.
    for key in [
        "data", "result", "results", "items", "list", "content", "holdings",
        "stocks", "balances", "assets", "orders", "executions", "prices",
        "body",
    ]:
        val = obj.get(key)
        if isinstance(val, list):
            return [x for x in val if isinstance(x, dict)]
        if isinstance(val, dict):
            nested = flatten_records(val)
            if nested:
                return nested

    # Search first list of dicts.
    for val in obj.values():
        if isinstance(val, list) and val and all(isinstance(x, dict) for x in val):
            return val
        if isinstance(val, dict):
            nested = flatten_records(val)
            if nested:
                return nested
    return []


def pick(row: dict, aliases: list[str]) -> Any:
    if not isinstance(row, dict):
        return ""
    lower = {str(k).lower(): k for k in row.keys()}
    for name in aliases:
        if name in row and row.get(name) not in (None, ""):
            return row.get(name)
        key = lower.get(name.lower())
        if key and row.get(key) not in (None, ""):
            return row.get(key)
    for k, v in row.items():
        kl = str(k).lower()
        for name in aliases:
            if name.lower() in kl and v not in (None, ""):
                return v
    return ""


@dataclass
class TossOperation:
    method: str
    path: str
    score: int = 0
    summary: str = ""
    operation_id: str = ""


class TossInvestClient:
    def __init__(self) -> None:
        self.base_url = env("TOSSINVEST_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
        self.openapi_url = env("TOSSINVEST_OPENAPI_URL", DEFAULT_OPENAPI_URL)
        self.client_id = env("TOSSINVEST_CLIENT_ID")
        self.client_secret = env("TOSSINVEST_CLIENT_SECRET")
        self.account = env("TOSSINVEST_ACCOUNT")
        self.token_url = env("TOSSINVEST_TOKEN_URL")
        self._account_checked = False
        self._access_token: str | None = None
        self._openapi: dict | None = None

    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def _request_raw(
        self,
        method: str,
        url: str,
        *,
        headers: dict | None = None,
        data: dict | None = None,
        timeout: int = 25,
    ) -> Any:
        headers = headers or {}
        body = None
        if data is not None:
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            headers.setdefault("Content-Type", "application/json")

        req = urllib.request.Request(url, method=method.upper(), data=body, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as res:
            raw = res.read().decode("utf-8", errors="replace")
            if not raw:
                return {}
            return json.loads(raw)

    def load_openapi(self) -> dict:
        if self._openapi is not None:
            return self._openapi
        cache = Path("docs/data/toss_openapi_cache.json")
        cache.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._openapi = self._request_raw("GET", self.openapi_url, timeout=20)
            cache.write_text(json.dumps(self._openapi, ensure_ascii=False, indent=2), encoding="utf-8")
            return self._openapi
        except Exception:
            if cache.exists():
                self._openapi = json.loads(cache.read_text(encoding="utf-8"))
                return self._openapi
            self._openapi = {}
            return self._openapi

    def discover_token_url(self) -> str:
        if self.token_url:
            return self.token_url
        spec = self.load_openapi()
        comps = spec.get("components", {}).get("securitySchemes", {})
        for sch in comps.values():
            flows = sch.get("flows", {}) if isinstance(sch, dict) else {}
            for flow in flows.values():
                token_url = flow.get("tokenUrl") if isinstance(flow, dict) else ""
                if token_url:
                    if token_url.startswith("http"):
                        return token_url
                    return self.base_url + "/" + token_url.lstrip("/")
        # fallback; can be overridden by TOSSINVEST_TOKEN_URL
        return self.base_url + "/oauth2/token"

    def access_token(self) -> str:
        if self._access_token:
            return self._access_token
        if not self.configured():
            raise RuntimeError("TOSSINVEST_CLIENT_ID / TOSSINVEST_CLIENT_SECRET is missing")

        token_url = self.discover_token_url()
        payloads = [
            {"grant_type": "client_credentials", "client_id": self.client_id, "client_secret": self.client_secret},
            {"grantType": "client_credentials", "clientId": self.client_id, "clientSecret": self.client_secret},
        ]
        basic = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        last_error = None

        for idx, data in enumerate(payloads):
            headers = {}
            if idx == 1:
                headers["Authorization"] = f"Basic {basic}"
            try:
                res = self._request_raw("POST", token_url, headers=headers, data=data)
                token = (
                    res.get("access_token")
                    or res.get("accessToken")
                    or res.get("token")
                    or res.get("data", {}).get("access_token")
                    or res.get("data", {}).get("accessToken")
                )
                if token:
                    self._access_token = str(token)
                    return self._access_token
            except Exception as e:
                last_error = e
                time.sleep(0.2)

        raise RuntimeError(f"Toss token issuance failed: {last_error!r}")

    def discover_default_account(self) -> str:
        """Return X-Tossinvest-Account value.

        Toss issues only CLIENT_ID and CLIENT_SECRET as app credentials.
        The account header is not a third API key. If TOSSINVEST_ACCOUNT is
        not provided, this method tries the read-only accounts API and picks
        the first account-like identifier.
        """
        if self.account:
            return self.account
        if self._account_checked:
            return ""
        self._account_checked = True

        try:
            data, _endpoint = self.get_accounts()
            records = flatten_records(data)
            for r in records:
                value = (
                    pick(r, ["accountId", "account_id", "accountNo", "accountNumber", "account", "id", "계좌번호", "계좌ID"])
                    or pick(r, ["securitiesAccountId", "tradingAccountId", "assetAccountId"])
                )
                if value:
                    self.account = str(value).strip()
                    return self.account
        except Exception:
            return ""
        return ""

    def auth_headers(self, *, account_required: bool = False) -> dict:
        headers = {"Authorization": f"Bearer {self.access_token()}"}
        if account_required:
            account = self.discover_default_account()
            if account:
                headers["X-Tossinvest-Account"] = account
        return headers

    def discover_operations(self, include: list[str], exclude: list[str] | None = None) -> list[TossOperation]:
        spec = self.load_openapi()
        paths = spec.get("paths", {})
        exclude = exclude or []
        out: list[TossOperation] = []

        for path, ops in paths.items():
            if not isinstance(ops, dict):
                continue
            for method, meta in ops.items():
                if method.lower() not in {"get", "post"} or not isinstance(meta, dict):
                    continue
                text = " ".join([
                    path,
                    str(method),
                    str(meta.get("operationId", "")),
                    str(meta.get("summary", "")),
                    str(meta.get("description", "")),
                    " ".join(map(str, meta.get("tags", []))),
                ]).lower()

                if any(x.lower() in text for x in exclude):
                    continue
                score = sum(3 for x in include if x.lower() in text)
                score += sum(1 for x in include if x.lower().replace("_", "-") in text)
                if score > 0:
                    out.append(
                        TossOperation(
                            method=method.upper(),
                            path=path,
                            score=score,
                            summary=str(meta.get("summary", "")),
                            operation_id=str(meta.get("operationId", "")),
                        )
                    )
        return sorted(out, key=lambda x: x.score, reverse=True)

    def _format_url(self, path: str, params: dict | None = None) -> str:
        if path.startswith("http"):
            base = path
        else:
            base = self.base_url + "/" + path.lstrip("/")
        params = {k: v for k, v in (params or {}).items() if v not in (None, "")}
        if params:
            sep = "&" if "?" in base else "?"
            return base + sep + urllib.parse.urlencode(params)
        return base

    def request_path(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        body: dict | None = None,
        account_required: bool = False,
    ) -> Any:
        path = self.interpolate_path(path, params or {})
        url = self._format_url(path, params if "{" not in path else None)
        return self._request_raw(method, url, headers=self.auth_headers(account_required=account_required), data=body)

    @staticmethod
    def interpolate_path(path: str, params: dict) -> str:
        out = path
        for key, value in list(params.items()):
            out = out.replace("{" + key + "}", urllib.parse.quote(str(value)))
        # Common OpenAPI param names
        for alias in ["symbol", "stockCode", "stock_code", "code", "ticker", "instrumentId", "instrument_id"]:
            if "{" + alias + "}" in out and params.get("symbol"):
                out = out.replace("{" + alias + "}", urllib.parse.quote(str(params.get("symbol"))))
        return out

    def request_first_operation(
        self,
        *,
        env_path: str,
        include: list[str],
        exclude: list[str] | None = None,
        params: dict | None = None,
        account_required: bool = False,
    ) -> tuple[Any, str]:
        override = env(env_path)
        tried: list[str] = []

        if override:
            tried.append(override)
            try:
                data = self.request_path("GET", override, params=params, account_required=account_required)
                return data, override
            except Exception as e:
                tried.append(f"{override} failed: {e!r}")

        for op in self.discover_operations(include=include, exclude=exclude):
            tried.append(f"{op.method} {op.path}")
            try:
                data = self.request_path(op.method, op.path, params=params, account_required=account_required)
                return data, op.path
            except Exception:
                continue

        raise RuntimeError(f"No Toss API endpoint succeeded for {env_path}. Tried: {tried[:8]}")

    # Read-only convenience methods
    def get_holdings(self) -> tuple[Any, str]:
        return self.request_first_operation(
            env_path="TOSSINVEST_HOLDINGS_PATH",
            include=["holding", "holdings", "balance", "balances", "asset", "assets", "보유", "잔고"],
            exclude=["orderbook", "price", "candle", "trade"],
            account_required=True,
        )

    def get_accounts(self) -> tuple[Any, str]:
        return self.request_first_operation(
            env_path="TOSSINVEST_ACCOUNTS_PATH",
            include=["account", "accounts", "계좌"],
            exclude=["order", "price", "candle"],
            account_required=False,
        )

    def get_price(self, symbol: str, market: str = "KR") -> tuple[Any, str]:
        symbol = normalize_code(symbol)
        params = {
            "symbol": symbol,
            "stockCode": symbol,
            "stock_code": symbol,
            "code": symbol,
            "ticker": symbol,
            "market": market,
            "exchange": market,
        }
        return self.request_first_operation(
            env_path="TOSSINVEST_PRICE_PATH",
            include=["price", "prices", "quote", "quotes", "현재가", "시세"],
            exclude=["orderbook", "candle", "trade", "order"],
            params=params,
            account_required=False,
        )

    def get_order_history(self) -> tuple[Any, str]:
        return self.request_first_operation(
            env_path="TOSSINVEST_ORDER_HISTORY_PATH",
            include=["order", "orders", "execution", "executions", "filled", "체결", "주문"],
            exclude=["create", "modify", "cancel", "buying-power", "sellable"],
            account_required=True,
        )


def status_row(status: str, message: str = "", source: str = "") -> dict:
    return {
        "status": status,
        "message": message,
        "source": source,
        "checked_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
    }
