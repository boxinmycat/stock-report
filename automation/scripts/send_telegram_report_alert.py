#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone, timedelta
import csv, os, urllib.parse, urllib.request

KST = timezone(timedelta(hours=9))

def now():
    return datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')

def read_csv(path, limit=20):
    p = Path(path)
    if not p.exists():
        return []
    for enc in ('utf-8-sig', 'utf-8', 'cp949', 'euc-kr'):
        try:
            with p.open(encoding=enc, newline='') as f:
                return list(csv.DictReader(f))[:limit]
        except Exception:
            pass
    return []

def status():
    out = {}
    for r in read_csv('docs/data/latest_publish_status.csv'):
        if r.get('key'):
            out[r['key']] = r.get('value', '')
    return out

def brief():
    rows = read_csv('docs/data/latest_holding_ai_briefing.csv', 5)
    if not rows:
        return 'Gemini AI 브리핑: 데이터 확인 필요'
    lines = ['Gemini AI 보유 브리핑']
    for r in rows[:3]:
        line = f"- {r.get('stock_name','')}: {r.get('ai_status','')} / {r.get('decision','')}"
        if r.get('ai_summary'):
            line += ' / ' + r.get('ai_summary', '')[:70]
        lines.append(line)
    return '\n'.join(lines)

def message():
    st = status()
    ss = (st.get('session') or 'MANUAL').upper()
    title = '[장전 리포트 완료]' if ss == 'AM' else '[장마감 리포트 완료]' if ss == 'PM' else '[주식 리포트 완료]'
    return f"""{title}

생성시각: {st.get('published_at') or now()}
세션: {ss}

{brief()}

최신 리포트:
https://boxinmycat.github.io/stock-report/latest/

Gemini AI 보유 브리핑:
https://boxinmycat.github.io/stock-report/details/holding_ai_briefing.html

보유종목:
https://boxinmycat.github.io/stock-report/v11_holdings/

뉴스상세:
https://boxinmycat.github.io/stock-report/details/naver_news.html
"""

def main():
    token = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
    chat = os.environ.get('TELEGRAM_CHAT_ID', '').strip()
    print('TELEGRAM_BOT_TOKEN:', 'OK' if token else 'MISSING')
    print('TELEGRAM_CHAT_ID:', 'OK' if chat else 'MISSING')
    if not token or not chat:
        return 0
    data = urllib.parse.urlencode({'chat_id': chat, 'text': message(), 'disable_web_page_preview': 'true'}).encode()
    with urllib.request.urlopen(f'https://api.telegram.org/bot{token}/sendMessage', data=data, timeout=15) as res:
        print('✅ Telegram alert sent')
        print(res.read().decode(errors='ignore')[:300])
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
