#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone, timedelta
import csv, os, urllib.parse, urllib.request

KST=timezone(timedelta(hours=9))

def now():
    return datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')

def read(path,n=20):
    if not Path(path).exists():
        return []
    for enc in ('utf-8-sig','utf-8','cp949','euc-kr'):
        try:
            with open(path,encoding=enc,newline='') as f:
                return list(csv.DictReader(f))[:n]
        except Exception:
            pass
    return []

def status():
    d={}
    for r in read('docs/data/latest_publish_status.csv'):
        if r.get('key'):
            d[r['key']]=r.get('value','')
    return d

def brief():
    st = status()
    ss = (st.get('session') or 'MANUAL').upper()
    if ss == 'AM':
        return 'AI 보유 브리핑: 비용 절감을 위해 장전에는 새로 생성하지 않고, 장마감 리포트에서 갱신합니다.'
    rows=read('docs/data/latest_holding_ai_briefing.csv',5)
    if not rows:
        return 'AI 보유 브리핑: 데이터 확인 필요'
    out=['AI 보유 브리핑']
    for r in rows[:3]:
        first = r.get('ai_three_line_summary','').splitlines()[0] if r.get('ai_three_line_summary') else r.get('ai_issue_summary','')[:60]
        out.append(f"- {r.get('stock_name','')}: {r.get('ai_sentiment','')} / {first}")
    return '\n'.join(out)

def msg():
    st=status()
    ss=(st.get('session') or 'MANUAL').upper()
    title='[장전 리포트 완료]' if ss=='AM' else '[장마감 리포트 완료]' if ss=='PM' else '[주식 리포트 완료]'
    return f"""{title}

생성시각: {st.get('published_at') or now()}
세션: {ss}

{brief()}

통합 홈:
https://boxinmycat.github.io/stock-report/mobile/

추천 TOP15:
https://boxinmycat.github.io/stock-report/details/legacy_top15.html

전체 추천 명단:
https://boxinmycat.github.io/stock-report/details/legacy_full_recommendations.html

진입 시나리오:
https://boxinmycat.github.io/stock-report/details/legacy_entry_scenario.html

추천 종목 분석:
https://boxinmycat.github.io/stock-report/details/recommendation_analysis.html

추천후보 상세:
https://boxinmycat.github.io/stock-report/details/candidate_detail.html

전략검증:
https://boxinmycat.github.io/stock-report/strategy/

Gemini AI 보유 브리핑:
https://boxinmycat.github.io/stock-report/details/holding_ai_briefing.html

보유종목:
https://boxinmycat.github.io/stock-report/v11_holdings/

주요 뉴스 요약:
https://boxinmycat.github.io/stock-report/details/naver_news.html
"""

def main():
    token=os.environ.get('TELEGRAM_BOT_TOKEN','').strip()
    chat=os.environ.get('TELEGRAM_CHAT_ID','').strip()
    print('TELEGRAM_BOT_TOKEN:','OK' if token else 'MISSING')
    print('TELEGRAM_CHAT_ID:','OK' if chat else 'MISSING')
    if not token or not chat:
        return 0
    data=urllib.parse.urlencode({'chat_id':chat,'text':msg(),'disable_web_page_preview':'true'}).encode()
    with urllib.request.urlopen(f'https://api.telegram.org/bot{token}/sendMessage',data=data,timeout=15) as r:
        print('✅ Telegram alert sent')
        print(r.read().decode(errors='ignore')[:300])
    return 0

if __name__=='__main__':
    raise SystemExit(main())
