#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone, timedelta
import csv, os, urllib.parse, urllib.request

KST = timezone(timedelta(hours=9))

def now():
    return datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')

def read(path, n=20):
    if not Path(path).exists():
        return []
    for enc in ('utf-8-sig','utf-8','cp949','euc-kr'):
        try:
            with open(path, encoding=enc, newline='') as f:
                return list(csv.DictReader(f))[:n]
        except Exception:
            pass
    return []

def status():
    d = {}
    for r in read('docs/data/latest_publish_status.csv'):
        if r.get('key'):
            d[r['key']] = r.get('value','')
    return d

def csv_diag():
    d = {}
    for r in read('docs/data/latest_schedule_diagnostics.csv', 30):
        if r.get('key'):
            d[r['key']] = r.get('value','')
    return d

def diagnostics():
    d = csv_diag()
    return {
        'event_name': os.environ.get('REPORT_EVENT_NAME') or d.get('event_name') or '',
        'event_schedule': os.environ.get('REPORT_EVENT_SCHEDULE') or d.get('event_schedule') or '',
        'kst_started': os.environ.get('REPORT_KST_STARTED_AT') or d.get('kst_started_at') or '',
        'utc_started': os.environ.get('REPORT_UTC_STARTED_AT') or d.get('utc_started_at') or '',
        'expected_kst': os.environ.get('REPORT_EXPECTED_KST') or d.get('expected_kst') or '',
        'expected_kind': os.environ.get('REPORT_EXPECTED_KIND') or d.get('expected_kind') or '',
        'skip_heavy_job': os.environ.get('SKIP_HEAVY_JOB') or d.get('skip_heavy_job') or d.get('skip_report') or 'false',
        'guard_reason': os.environ.get('REPORT_GUARD_REASON') or d.get('guard_reason') or '',
        'report_session': os.environ.get('REPORT_SESSION') or d.get('report_session') or '',
    }

def brief():
    st = status()
    ss = (os.environ.get('REPORT_SESSION') or st.get('session') or 'MANUAL').upper()
    if ss == 'AM':
        return 'AI 보유 브리핑: 장전에는 비용 절감을 위해 새로 생성하지 않고 장마감 리포트에서 갱신합니다.'
    rows = read('docs/data/latest_holding_ai_briefing.csv', 5)
    if not rows:
        return 'AI 보유 브리핑: 데이터 확인 필요'
    out = ['AI 보유 브리핑']
    for r in rows[:3]:
        action = r.get('ai_action_headline') or r.get('decision') or ''
        first = r.get('ai_three_line_summary','').splitlines()[0] if r.get('ai_three_line_summary') else r.get('ai_issue_summary','')[:60]
        out.append(f"- {r.get('stock_name','')}: {action} / {r.get('ai_sentiment','')} / {first}")
    return '\n'.join(out)

def gemini_health_line():
    rows = read('docs/data/latest_gemini_health.csv', 3)
    if not rows:
        return 'Gemini: health check not run in this session'
    r = rows[0]
    return f"Gemini: {r.get('status','')} / {r.get('model','')}"

def blocked_msg(diag):
    return f"""⚠️ [스케줄 실행 자동 차단 알림]

GitHub Actions scheduled run이 허용 시간 밖에서 시작되어 무거운 리포트 생성 작업을 자동 차단했습니다.

실행 이벤트: {diag.get('event_name')}
실행 cron: {diag.get('event_schedule')}
예상 KST: {diag.get('expected_kst')}
실제 시작 KST: {diag.get('kst_started')}
차단 사유: {diag.get('guard_reason')}
세션: {diag.get('report_session')}

수동 실행(workflow_dispatch)은 차단하지 않습니다.
"""

def normal_msg(diag):
    st = status()
    ss = (os.environ.get('REPORT_SESSION') or st.get('session') or diag.get('report_session') or 'MANUAL').upper()
    title = '[장전 리포트 완료]' if ss == 'AM' else '[장마감 리포트 완료]' if ss == 'PM' else '[수동 테스트 리포트 완료]' if ss == 'MANUAL' else '[주식 리포트 완료]'
    return f"""{title}

생성시각: {st.get('published_at') or now()}
세션: {ss}
실행 이벤트: {diag.get('event_name')}
실행 cron: {diag.get('event_schedule')}
예상 KST: {diag.get('expected_kst')}
실제 시작 KST: {diag.get('kst_started')}
가드 상태: {diag.get('guard_reason')}

{brief()}
{gemini_health_line()}

모바일 홈:
https://boxinmycat.github.io/stock-report/mobile/

추천 TOP15:
https://boxinmycat.github.io/stock-report/details/legacy_top15.html

전체 추천 명단:
https://boxinmycat.github.io/stock-report/details/legacy_full_recommendations.html

추천후보 상세:
https://boxinmycat.github.io/stock-report/details/candidate_detail.html

Gemini AI 보유 브리핑:
https://boxinmycat.github.io/stock-report/details/holding_ai_briefing.html

보유종목:
https://boxinmycat.github.io/stock-report/v11_holdings/

주요 뉴스 요약:
https://boxinmycat.github.io/stock-report/details/naver_news.html

실행 상태:
https://boxinmycat.github.io/stock-report/details/run_manifest.html
"""

def msg():
    diag = diagnostics()
    if str(diag.get('skip_heavy_job')).lower() == 'true':
        return blocked_msg(diag)
    return normal_msg(diag)

def main():
    token = os.environ.get('TELEGRAM_BOT_TOKEN','').strip()
    chat = os.environ.get('TELEGRAM_CHAT_ID','').strip()
    print('TELEGRAM_BOT_TOKEN:', 'OK' if token else 'MISSING')
    print('TELEGRAM_CHAT_ID:', 'OK' if chat else 'MISSING')
    print('SKIP_HEAVY_JOB:', os.environ.get('SKIP_HEAVY_JOB',''))
    print('REPORT_GUARD_REASON:', os.environ.get('REPORT_GUARD_REASON',''))
    if not token or not chat:
        return 0
    data = urllib.parse.urlencode({'chat_id': chat, 'text': msg(), 'disable_web_page_preview': 'true'}).encode()
    with urllib.request.urlopen(f'https://api.telegram.org/bot{token}/sendMessage', data=data, timeout=15) as r:
        print('✅ Telegram alert sent')
        print(r.read().decode(errors='ignore')[:300])
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
