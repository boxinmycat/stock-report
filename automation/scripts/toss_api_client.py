#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Toss Invest Open API read-only client.

v12.2.31 endpoint-group strict routing

핵심 수정:
- market-info / exchange-rate API를 주식 현재가/잔고/체결내역 후보에서 완전히 제외
- 현재가는 market-data / price / quote 계열에서만 탐색
- 보유종목은 account / asset / holding 계열에서만 탐색
- 체결내역은 order execution/history 계열에서만 탐색
- 정확한 endpoint는 OpenAPI JSON을 읽어 tag/path/operationId 기준으로 분리
- API 실패 시 리포트 전체가 죽지 않도록 debug CSV 저장

필수 GitHub Secrets:
- TOSSINVEST_CLIENT_ID
- TOSSINVEST_CLIENT_SECRET

선택 GitHub Secrets:
- TOSSINVEST_ACCOUNT
- TOSSINVEST_TOKEN_URL
- TOSSINVEST_ACCOUNTS_PATH
- TOSSINVEST_HOLDINGS_PATH
- TOSSINVEST_PRICE_PATH
- TOSSINVEST_ORDER_HISTORY_PATH
- TOSSINVEST_ENABLE_TRADE_HISTORY=true
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import base64
import csv
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

    text = text.replace("=", "")
    text = text.replace('"', "")
    text = text.replace("'", "")
    text = text.replace(",", "")
    text = text.replace(" ", "")

    if re.fullmatch(r"\d+\.0", text):
        text = text[:-2]

    text = re.sub(r"[^0-9A-Z]", "", text)

    if not text:
        return ""

    # 국내 종목코드 앞자리 0 보존
    if re.fullmatch(r"\d+", text):
        return text.zfill(6)

    # 알파뉴메릭 ETF/ETN 코드 보존
    return text


def flatten_records(obj: Any) -> list[dict]:
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]

    if not isinstance(obj, dict):
        return []

    common_keys = [
        "data",
        "result",
        "results",
        "items",
        "list",
        "content",
        "holdings",
        "stocks",
        "balances",
        "assets",
        "orders",
        "executions",
        "prices",
        "accounts",
        "body",
    ]

    for key in common_keys:
        val = obj.get(key)

        if isinstance(val, list):
            return [x for x in val if isinstance(x, dict)]

        if isinstance(val, dict):
            nested = flatten_records(val)
            if nested:
                return nested

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


def status_row(status: str, message: str = "", source: str = "") -> dict:
    return {
        "status": status,
        "message": message,
        "source": source,
        "checked_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
    }


class TossApiError(RuntimeError):
    def __init__(self, message: str, *, status: str = "", body: str = "", url: str = ""):
        super().__init__(message)
        self.status = status
        self.body = body
        self.url = url


@dataclass
class TossOperation:
    method: str
    path: str
    score: int = 0
    summary: str = ""
    operation_id: str = ""
    tags: str = ""


class TossInvestClient:
    def __init__(self) -> None:
        self.base_url = env("TOSSINVEST_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
        self.openapi_url = env("TOSSINVEST_OPENAPI_URL", DEFAULT_OPENAPI_URL)

        self.client_id = env("TOSSINVEST_CLIENT_ID")
        self.client_secret = env("TOSSINVEST_CLIENT_SECRET")
        self.account = env("TOSSINVEST_ACCOUNT")

        self.token_url = env("TOSSINVEST_TOKEN_URL")

        self._access_token: str | None = None
        self._openapi: dict | None = None
        self._account_checked = False

        self.debug_rows: list[dict] = []

    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def add_debug(
        self,
        kind: str,
        target: str,
        status: str,
        message: str = "",
        body: str = "",
    ) -> None:
        body = str(body or "")
        if len(body) > 800:
            body = body[:800]

        self.debug_rows.append(
            {
                "checked_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                "kind": kind,
                "target": target,
                "status": status,
                "message": str(message or "")[:800],
                "body_preview": body,
            }
        )

    def write_debug_csv(self, path: str = "docs/data/toss_api_debug_report.csv") -> None:
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)

            fields = [
                "checked_at",
                "kind",
                "target",
                "status",
                "message",
                "body_preview",
            ]

            with p.open("w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()

                for row in self.debug_rows:
                    writer.writerow({k: row.get(k, "") for k in fields})

        except Exception:
            pass

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

        req = urllib.request.Request(
            url,
            method=method.upper(),
            data=body,
            headers=headers,
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as res:
                raw = res.read().decode("utf-8", errors="replace")

                if not raw:
                    return {}

                return json.loads(raw)

        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace")
            raise TossApiError(
                f"HTTP {e.code}",
                status=str(e.code),
                body=raw,
                url=url,
            ) from e

        except Exception as e:
            raise TossApiError(
                type(e).__name__,
                status="ERROR",
                body=repr(e),
                url=url,
            ) from e

    def load_openapi(self) -> dict:
        if self._openapi is not None:
            return self._openapi

        cache = Path("docs/data/toss_openapi_cache.json")
        cache.parent.mkdir(parents=True, exist_ok=True)

        try:
            self._openapi = self._request_raw("GET", self.openapi_url, timeout=20)
            cache.write_text(
                json.dumps(self._openapi, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self.dump_openapi_paths()
            return self._openapi

        except Exception as e:
            self.add_debug(
                "openapi",
                self.openapi_url,
                getattr(e, "status", "ERROR"),
                repr(e),
                getattr(e, "body", ""),
            )

            if cache.exists():
                self._openapi = json.loads(cache.read_text(encoding="utf-8"))
                self.dump_openapi_paths()
                return self._openapi

            self._openapi = {}
            return self._openapi

    def dump_openapi_paths(self, path: str = "docs/data/toss_openapi_paths.csv") -> None:
        try:
            spec = self._openapi or {}
            paths = spec.get("paths", {})

            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)

            fields = [
                "method",
                "path",
                "operationId",
                "summary",
                "tags",
            ]

            with p.open("w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()

                for api_path, ops in sorted(paths.items()):
                    if not isinstance(ops, dict):
                        continue

                    for method, meta in ops.items():
                        if not isinstance(meta, dict):
                            continue

                        writer.writerow(
                            {
                                "method": method.upper(),
                                "path": api_path,
                                "operationId": meta.get("operationId", ""),
                                "summary": meta.get("summary", ""),
                                "tags": ",".join(map(str, meta.get("tags", []))),
                            }
                        )

        except Exception:
            pass

    def discover_token_url(self) -> str:
        if self.token_url:
            return self.token_url

        spec = self.load_openapi()
        components = spec.get("components", {})
        schemes = components.get("securitySchemes", {})

        for scheme in schemes.values():
            if not isinstance(scheme, dict):
                continue

            flows = scheme.get("flows", {})
            if not isinstance(flows, dict):
                continue

            for flow in flows.values():
                if not isinstance(flow, dict):
                    continue

                token_url = flow.get("tokenUrl")
                if token_url:
                    if str(token_url).startswith("http"):
                        return str(token_url)
                    return self.base_url + "/" + str(token_url).lstrip("/")

        return self.base_url + "/oauth2/token"

    def access_token(self) -> str:
        if self._access_token:
            return self._access_token

        if not self.configured():
            raise RuntimeError("TOSSINVEST_CLIENT_ID / TOSSINVEST_CLIENT_SECRET is missing")

        token_url = self.discover_token_url()

        basic = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()

        payloads = [
            (
                {
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                {},
            ),
            (
                {
                    "grantType": "client_credentials",
                    "clientId": self.client_id,
                    "clientSecret": self.client_secret,
                },
                {"Authorization": f"Basic {basic}"},
            ),
        ]

        last_error = None

        for data, headers in payloads:
            try:
                res = self._request_raw(
                    "POST",
                    token_url,
                    headers=headers,
                    data=data,
                )

                token = (
                    res.get("access_token")
                    or res.get("accessToken")
                    or res.get("token")
                    or res.get("data", {}).get("access_token")
                    or res.get("data", {}).get("accessToken")
                )

                if token:
                    self._access_token = str(token)
                    self.add_debug("auth", token_url, "OK", "token issued")
                    return self._access_token

                self.add_debug(
                    "auth",
                    token_url,
                    "NO_TOKEN",
                    "token field not found",
                    json.dumps(res, ensure_ascii=False)[:500],
                )

            except Exception as e:
                last_error = e
                self.add_debug(
                    "auth",
                    token_url,
                    getattr(e, "status", "ERROR"),
                    repr(e),
                    getattr(e, "body", ""),
                )
                time.sleep(0.2)

        raise RuntimeError(f"Toss token issuance failed: {last_error!r}")

    def auth_headers(self, *, account_required: bool = False) -> dict:
        headers = {"Authorization": f"Bearer {self.access_token()}"}

        if account_required:
            account = self.discover_default_account()
            if account:
                headers["X-Tossinvest-Account"] = account

        return headers

    @staticmethod
    def operation_text(path: str, method: str, meta: dict) -> str:
        return " ".join(
            [
                path,
                method,
                str(meta.get("operationId", "")),
                str(meta.get("summary", "")),
                str(meta.get("description", "")),
                " ".join(map(str, meta.get("tags", []))),
            ]
        ).lower()

    @staticmethod
    def operation_tags(meta: dict) -> str:
        return " ".join(map(str, meta.get("tags", []))).lower()

    def discover_operations(
        self,
        *,
        include: list[str],
        exclude: list[str] | None = None,
        required_tag_keywords: list[str] | None = None,
        forbidden_tag_keywords: list[str] | None = None,
        max_results: int = 20,
    ) -> list[TossOperation]:
        spec = self.load_openapi()
        paths = spec.get("paths", {})

        exclude = exclude or []
        required_tag_keywords = required_tag_keywords or []
        forbidden_tag_keywords = forbidden_tag_keywords or []

        out: list[TossOperation] = []

        for api_path, ops in paths.items():
            if not isinstance(ops, dict):
                continue

            for method, meta in ops.items():
                if method.lower() not in {"get", "post"}:
                    continue

                if not isinstance(meta, dict):
                    continue

                text = self.operation_text(api_path, method, meta)
                tags = self.operation_tags(meta)

                # 태그 기반 차단: market-info/exchange-rate가 price/order/holdings에 섞이지 않도록 방어
                if any(word.lower() in tags for word in forbidden_tag_keywords):
                    continue

                # 태그 기반 필수 조건
                if required_tag_keywords:
                    if not any(word.lower() in tags for word in required_tag_keywords):
                        continue

                # 전체 텍스트 기반 차단
                if any(word.lower() in text for word in exclude):
                    continue

                score = 0

                for word in include:
                    w = word.lower()

                    if w in text:
                        score += 5

                    if w.replace("_", "-") in text:
                        score += 2

                    if w in tags:
                        score += 3

                if score <= 0:
                    continue

                out.append(
                    TossOperation(
                        method=method.upper(),
                        path=api_path,
                        score=score,
                        summary=str(meta.get("summary", "")),
                        operation_id=str(meta.get("operationId", "")),
                        tags=",".join(map(str, meta.get("tags", []))),
                    )
                )

        return sorted(out, key=lambda x: x.score, reverse=True)[:max_results]

    def _format_url(self, path: str, params: dict | None = None) -> str:
        if path.startswith("http"):
            base = path
        else:
            base = self.base_url + "/" + path.lstrip("/")

        params = {
            k: v
            for k, v in (params or {}).items()
            if v not in (None, "")
        }

        if params:
            sep = "&" if "?" in base else "?"
            return base + sep + urllib.parse.urlencode(params)

        return base

    @staticmethod
    def interpolate_path(path: str, params: dict) -> tuple[str, dict]:
        out = path
        params = dict(params or {})

        placeholders = re.findall(r"\{([^}]+)\}", path)

        for name in placeholders:
            key = name
            lower = name.lower()

            if lower in params:
                value = params.pop(lower)
            elif key in params:
                value = params.pop(key)
            elif any(x in lower for x in ["market", "exchange", "country", "region"]):
                value = params.get("market") or params.get("exchange") or "KR"
            elif any(x in lower for x in ["symbol", "stock", "code", "ticker", "instrument"]):
                value = params.get("symbol") or params.get("stockCode") or params.get("code")
            elif any(x in lower for x in ["orderid", "order_id"]):
                value = params.get("orderId") or params.get("order_id") or ""
            else:
                value = params.get("symbol") or params.get("stockCode") or params.get("code")

            out = out.replace("{" + name + "}", urllib.parse.quote(str(value or "")))

        return out, params

    def request_path(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        body: dict | None = None,
        account_required: bool = False,
        send_query_params: bool = True,
    ) -> Any:
        path2, remaining_params = self.interpolate_path(path, params or {})

        url = self._format_url(
            path2,
            remaining_params if send_query_params else None,
        )

        try:
            data = self._request_raw(
                method,
                url,
                headers=self.auth_headers(account_required=account_required),
                data=body,
            )

            self.add_debug("request", f"{method} {path}", "OK", f"url={url}")
            return data

        except Exception as e:
            self.add_debug(
                "request",
                f"{method} {path}",
                getattr(e, "status", "ERROR"),
                repr(e),
                getattr(e, "body", ""),
            )
            raise

    def request_first_operation(
        self,
        *,
        env_path: str,
        include: list[str],
        exclude: list[str] | None = None,
        params: dict | None = None,
        account_required: bool = False,
        required_tag_keywords: list[str] | None = None,
        forbidden_tag_keywords: list[str] | None = None,
        max_attempts: int = 6,
        send_query_params: bool = True,
    ) -> tuple[Any, str]:
        override = env(env_path)

        if override:
            data = self.request_path(
                "GET",
                override,
                params=params,
                account_required=account_required,
                send_query_params=send_query_params,
            )
            return data, override

        operations = self.discover_operations(
            include=include,
            exclude=exclude,
            required_tag_keywords=required_tag_keywords,
            forbidden_tag_keywords=forbidden_tag_keywords,
            max_results=max_attempts,
        )

        tried: list[str] = []

        for op in operations:
            tried.append(f"{op.method} {op.path}")

            try:
                data = self.request_path(
                    op.method,
                    op.path,
                    params=params,
                    account_required=account_required,
                    send_query_params=send_query_params,
                )
                return data, op.path

            except Exception:
                continue

        raise RuntimeError(
            f"No Toss API endpoint succeeded for {env_path}. Tried: {tried}"
        )

    def get_accounts(self) -> tuple[Any, str]:
        return self.request_first_operation(
            env_path="TOSSINVEST_ACCOUNTS_PATH",
            include=[
                "account",
                "accounts",
                "계좌",
            ],
            exclude=[
                "orderbook",
                "price",
                "prices",
                "quote",
                "quotes",
                "current",
                "trade",
                "trades",
                "exchange-rate",
                "exchange_rate",
                "exchange rate",
                "calendar",
                "commissions",
                "order",
                "orders",
            ],
            required_tag_keywords=[
                "account",
                "asset",
                "계좌",
                "자산",
            ],
            forbidden_tag_keywords=[
                "market-info",
                "market data",
                "market-data",
                "order",
            ],
            account_required=False,
            max_attempts=4,
        )

    def discover_default_account(self) -> str:
        if self.account:
            return self.account

        if self._account_checked:
            return ""

        self._account_checked = True

        try:
            data, endpoint = self.get_accounts()
            records = flatten_records(data)

            for row in records:
                value = (
                    pick(
                        row,
                        [
                            "accountId",
                            "account_id",
                            "accountNo",
                            "accountNumber",
                            "account",
                            "id",
                            "계좌번호",
                            "계좌ID",
                        ],
                    )
                    or pick(
                        row,
                        [
                            "securitiesAccountId",
                            "tradingAccountId",
                            "assetAccountId",
                        ],
                    )
                )

                if value:
                    self.account = str(value).strip()
                    self.add_debug("account", endpoint, "OK", "auto discovered account")
                    return self.account

            self.add_debug(
                "account",
                endpoint,
                "NO_ACCOUNT_FIELD",
                "account-like field was not found",
            )

        except Exception as e:
            self.add_debug(
                "account",
                "auto_discovery",
                getattr(e, "status", "ERROR"),
                repr(e),
                getattr(e, "body", ""),
            )

        return ""

    def get_holdings(self) -> tuple[Any, str]:
        if not self.account and not env("TOSSINVEST_HOLDINGS_PATH"):
            self.discover_default_account()

            if not self.account:
                raise RuntimeError(
                    "NEEDS_TOSSINVEST_ACCOUNT: account auto discovery failed. "
                    "Add TOSSINVEST_ACCOUNT or TOSSINVEST_ACCOUNTS_PATH after checking docs/data/toss_openapi_paths.csv."
                )

        return self.request_first_operation(
            env_path="TOSSINVEST_HOLDINGS_PATH",
            include=[
                "holding",
                "holdings",
                "balance",
                "balances",
                "asset",
                "assets",
                "portfolio",
                "보유",
                "잔고",
                "자산",
            ],
            exclude=[
                "orderbook",
                "price",
                "prices",
                "quote",
                "quotes",
                "current",
                "candle",
                "candles",
                "trade",
                "trades",
                "exchange-rate",
                "exchange_rate",
                "exchange rate",
                "calendar",
                "commissions",
                "order",
                "orders",
                "{orderId}",
            ],
            required_tag_keywords=[
                "account",
                "asset",
                "holding",
                "balance",
                "계좌",
                "자산",
                "보유",
                "잔고",
            ],
            forbidden_tag_keywords=[
                "market-info",
                "market data",
                "market-data",
                "order",
            ],
            account_required=True,
            max_attempts=5,
        )

    def get_price(self, symbol: str, market: str = "KR") -> tuple[Any, str]:
        symbol = normalize_code(symbol)

        params = {
            "symbol": symbol,
            "stockCode": symbol,
            "stock_code": symbol,
            "code": symbol,
            "ticker": symbol,
            "instrumentId": symbol,
            "instrument_id": symbol,
            "market": market,
            "exchange": market,
        }

        return self.request_first_operation(
            env_path="TOSSINVEST_PRICE_PATH",
            include=[
                "price",
                "prices",
                "quote",
                "quotes",
                "current",
                "current-price",
                "last",
                "현재가",
                "시세",
            ],
            exclude=[
                "exchange-rate",
                "exchange_rate",
                "exchange rate",
                "calendar",
                "market-info",
                "account",
                "accounts",
                "holding",
                "holdings",
                "balance",
                "balances",
                "asset",
                "assets",
                "order",
                "orders",
                "orderbook",
                "candle",
                "candles",
                "trading-hours",
                "price-limit",
            ],
            required_tag_keywords=[
                "market-data",
                "market data",
                "price",
                "quote",
                "시세",
            ],
            forbidden_tag_keywords=[
                "market-info",
                "account",
                "asset",
                "order",
            ],
            params=params,
            account_required=False,
            max_attempts=6,
            send_query_params=True,
        )

    def get_order_history(self) -> tuple[Any, str]:
        if (
            env("TOSSINVEST_ENABLE_TRADE_HISTORY", "false").lower()
            not in {"1", "true", "yes", "y"}
            and not env("TOSSINVEST_ORDER_HISTORY_PATH")
        ):
            raise RuntimeError(
                "SKIPPED_BY_DEFAULT: trade/order history is disabled until exact endpoint is confirmed. "
                "Set TOSSINVEST_ENABLE_TRADE_HISTORY=true or TOSSINVEST_ORDER_HISTORY_PATH."
            )

        if not self.account and not env("TOSSINVEST_ORDER_HISTORY_PATH"):
            self.discover_default_account()

            if not self.account:
                raise RuntimeError(
                    "NEEDS_TOSSINVEST_ACCOUNT: order history requires account header."
                )

        return self.request_first_operation(
            env_path="TOSSINVEST_ORDER_HISTORY_PATH",
            include=[
                "execution",
                "executions",
                "order-history",
                "order history",
                "orders",
                "filled",
                "fills",
                "체결",
                "주문내역",
            ],
            exclude=[
                "orderbook",
                "market-data",
                "market data",
                "market-info",
                "trades",
                "exchange-rate",
                "exchange_rate",
                "exchange rate",
                "calendar",
                "commissions",
                "create",
                "modify",
                "cancel",
                "buying-power",
                "sellable",
                "{orderId}",
            ],
            required_tag_keywords=[
                "order",
                "주문",
                "체결",
            ],
            forbidden_tag_keywords=[
                "market-info",
                "market-data",
                "account",
                "asset",
            ],
            account_required=True,
            max_attempts=5,
        )

    def get_exchange_rate(self) -> tuple[Any, str]:
        """
        환율 전용.

        중요:
        이 함수는 현재가/보유종목/체결내역 조회에 절대 사용하지 않는다.
        사용자가 지적한 market-info/getExchangeRate 계열은 여기에서만 사용한다.
        """
        return self.request_first_operation(
            env_path="TOSSINVEST_EXCHANGE_RATE_PATH",
            include=[
                "exchange-rate",
                "exchange_rate",
                "exchange rate",
                "환율",
            ],
            exclude=[
                "price",
                "quote",
                "holding",
                "account",
                "order",
                "orderbook",
                "trades",
            ],
            required_tag_keywords=[
                "market-info",
                "market info",
                "환율",
            ],
            forbidden_tag_keywords=[
                "market-data",
                "account",
                "asset",
                "order",
            ],
            account_required=False,
            max_attempts=4,
        )
```
