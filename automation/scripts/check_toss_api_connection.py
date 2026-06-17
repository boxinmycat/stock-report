#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path
import csv
import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error


BASE_URL = os.environ.get("TOSSINVEST_BASE_URL", "https://openapi.tossinvest.com").rstrip("/")
OPENAPI_URL = os.environ.get(
    "TOSSINVEST_OPENAPI_URL",
    "https://openapi.tossinvest.com/openapi-docs/latest/openapi.json",
)
TOKEN_URL = os.environ.get("TOSSINVEST_TOKEN_URL", f"{BASE_URL}/oauth2/token")

CLIENT_ID = os.environ.get("TOSSINVEST_CLIENT_ID", "").strip()
CLIENT_SECRET = os.environ.get("TOSSINVEST_CLIENT_SECRET", "").strip()

OUT_DIR = Path("docs/data")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def now_utc() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())


def write_status(rows):
    path = OUT_DIR / "toss_connection_check.csv"
    fields = ["checked_at", "step", "status", "message", "body_preview"]

    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def http_json(method: str, url: str, *, headers=None, data=None, timeout=20):
    headers = headers or {}
    body = None

    if data is not None:
        body = urllib.parse.urlencode(data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"

    req = urllib.request.Request(url, method=method, data=body, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            raw = res.read().decode("utf-8", errors="replace")
            return res.status, raw, json.loads(raw) if raw else {}

    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        return e.code, raw, None

    except Exception as e:
        return "ERROR", repr(e), None


def dump_openapi_paths(spec):
    path = OUT_DIR / "toss_openapi_paths.csv"
    fields = ["method", "path", "operationId", "summary", "tags"]

    paths = spec.get("paths", {}) if isinstance(spec, dict) else {}

    with path.open("w", newline="", encoding="utf-8-sig") as f:
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


def main():
    rows = []

    if not CLIENT_ID or not CLIENT_SECRET:
        rows.append(
            {
                "checked_at": now_utc(),
                "step": "env",
                "status": "FAIL",
                "message": "TOSSINVEST_CLIENT_ID 또는 TOSSINVEST_CLIENT_SECRET이 없습니다.",
                "body_preview": "",
            }
        )
        write_status(rows)
        print("❌ Toss API 키 환경변수 없음")
        return 0

    rows.append(
        {
            "checked_at": now_utc(),
            "step": "env",
            "status": "OK",
            "message": "CLIENT_ID / CLIENT_SECRET 감지됨",
            "body_preview": "",
        }
    )

    # 1. OpenAPI JSON 확인
    status, raw, spec = http_json("GET", OPENAPI_URL)

    rows.append(
        {
            "checked_at": now_utc(),
            "step": "openapi",
            "status": str(status),
            "message": OPENAPI_URL,
            "body_preview": raw[:300],
        }
    )

    if isinstance(spec, dict):
        dump_openapi_paths(spec)
        print("✅ OpenAPI JSON 확인 및 toss_openapi_paths.csv 저장 완료")
    else:
        print("⚠️ OpenAPI JSON 파싱 실패")

    # 2. OAuth token form-urlencoded 확인
    payloads = [
        {
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        {
            "grantType": "client_credentials",
            "clientId": CLIENT_ID,
            "clientSecret": CLIENT_SECRET,
        },
    ]

    token_ok = False

    for idx, payload in enumerate(payloads, start=1):
        status, raw, data = http_json("POST", TOKEN_URL, data=payload)

        token = ""
        if isinstance(data, dict):
            token = (
                data.get("access_token")
                or data.get("accessToken")
                or data.get("token")
                or data.get("data", {}).get("access_token")
                or data.get("data", {}).get("accessToken")
                or ""
            )

        rows.append(
            {
                "checked_at": now_utc(),
                "step": f"token_payload_{idx}",
                "status": "OK" if token else str(status),
                "message": "token issued" if token else TOKEN_URL,
                "body_preview": raw[:500],
            }
        )

        if token:
            token_ok = True
            print("✅ Toss access token 발급 성공")
            break

    if not token_ok:
        print("❌ Toss access token 발급 실패")

    write_status(rows)
    print("✅ 저장: docs/data/toss_connection_check.csv")
    print("✅ 저장: docs/data/toss_openapi_paths.csv")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
