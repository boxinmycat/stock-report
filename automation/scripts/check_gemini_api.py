#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone, timedelta
import csv
import json
import os
import urllib.parse
import urllib.request
import urllib.error

KST = timezone(timedelta(hours=9))


def now_kst() -> str:
    return datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')


def write_status(rows):
    path = Path('docs/data/latest_gemini_health.csv')
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ['checked_at', 'model', 'status', 'message']
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def call_model(key: str, model: str) -> tuple[bool, str]:
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{urllib.parse.quote(model)}:generateContent'
    payload = {
        'contents': [{'parts': [{'text': 'Reply with OK only.'}]}],
        'generationConfig': {'temperature': 0, 'maxOutputTokens': 8},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'x-goog-api-key': key},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            data = json.loads(res.read().decode('utf-8'))
        text = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
        return True, (text or 'OK').strip()[:200]
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='ignore')[:500]
        return False, f'HTTP {e.code}: {body}'
    except Exception as e:
        return False, f'{type(e).__name__}: {repr(e)}'


def main() -> int:
    key = os.environ.get('GEMINI_API_KEY', '').strip()
    primary = os.environ.get('GEMINI_MODEL', 'gemini-3.5-flash').strip() or 'gemini-3.5-flash'
    models = []
    for m in [primary, 'gemini-2.5-flash', 'gemini-2.5-flash-lite']:
        if m and m not in models:
            models.append(m)

    rows = []
    if not key:
        rows.append({'checked_at': now_kst(), 'model': primary, 'status': 'missing_key', 'message': 'GEMINI_API_KEY is not set in GitHub Actions secrets.'})
        write_status(rows)
        print('⚠️ GEMINI_API_KEY missing')
        return 0

    any_ok = False
    for model in models:
        ok, msg = call_model(key, model)
        rows.append({'checked_at': now_kst(), 'model': model, 'status': 'ok' if ok else 'fail', 'message': msg})
        print(f"{'✅' if ok else '⚠️'} Gemini health {model}: {msg}")
        if ok:
            any_ok = True
            break

    write_status(rows)
    if not any_ok:
        print('⚠️ Gemini health check failed for all models. Report will continue with fallback where possible.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
