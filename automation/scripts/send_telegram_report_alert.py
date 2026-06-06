#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone, timedelta
import csv, os, urllib.parse, urllib.request, urllib.error
KST=timezone(timedelta(hours=9))
def rows(p,limit=20):
    if not Path(p).exists(): return []
    for e in ['utf-8-sig','utf-8','cp949','euc-kr']:
        try:
            with open(p,encoding=e,newline='') as f: return list(csv.DictReader(f))[:limit]
        except Exception: pass
    return []
def pick(r,names):
    mp={str(k).lower().strip():k for k in r.keys()}
    for n in names:
        if n.lower() in mp: return str(r.get(mp[n.lower()],'')).strip()
    return ''
def status():
    d={}
    for r in rows('docs/data/latest_publish_status.csv'):
        if r.get('key'): d[r['key']]=r.get('value','')
    return d
def msg():
    st=status(); sess=(st.get('session') or '').upper() or ('AM' if datetime.now(KST).hour<12 else 'PM')
    title='[장전 리포트 완료]' if sess=='AM' else '[장마감 리포트 완료]' if sess=='PM' else '[주식 리포트 완료]'
    cand=rows('docs/data/latest_candidates.csv',5); lines=[]
    for i,r in enumerate(cand,1):
        name=pick(r,['stock_name','종목명','name']); score=pick(r,['score','점수','추천점수'])
        if name: lines.append(f'{i}. {name}'+(f' / 점수 {score}' if score else ''))
    hold=rows('docs/data/latest_holding_deep_analysis.csv',100); cnt={}
    for r in hold:
        d=pick(r,['decision','판단']) or 'UNKNOWN'; cnt[d]=cnt.get(d,0)+1
    hold_txt=', '.join(f'{k} {v}개' for k,v in sorted(cnt.items())) if cnt else '데이터 확인 필요'
    return f"""{title}

생성시각: {st.get('published_at') or datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')}
세션: {sess}

추천후보 TOP
{chr(10).join(lines) if lines else '데이터 확인 필요'}

보유종목 판단: {hold_txt}

모바일 홈:
https://boxinmycat.github.io/stock-report/mobile/

최신 리포트:
https://boxinmycat.github.io/stock-report/latest/

보유종목:
https://boxinmycat.github.io/stock-report/v11_holdings/

전략검증:
https://boxinmycat.github.io/stock-report/strategy/
"""
def send(text):
    token=os.getenv('TELEGRAM_BOT_TOKEN','').strip(); chat=os.getenv('TELEGRAM_CHAT_ID','').strip()
    print('TELEGRAM_BOT_TOKEN:', 'OK' if token else 'MISSING'); print('TELEGRAM_CHAT_ID:', 'OK' if chat else 'MISSING')
    if not token or not chat: print('⚠️ Telegram secrets missing. Skip alert.'); return 0
    data=urllib.parse.urlencode({'chat_id':chat,'text':text,'disable_web_page_preview':'true'}).encode()
    try:
        with urllib.request.urlopen(f'https://api.telegram.org/bot{token}/sendMessage',data=data,timeout=15) as res:
            print('✅ Telegram alert sent'); print(res.read().decode(errors='ignore')[:300]); return 0
    except urllib.error.HTTPError as e:
        print('❌ Telegram HTTP error:',e.code); print(e.read().decode(errors='ignore')[:500]); return 1
    except Exception as e:
        print('❌ Telegram alert error:',repr(e)); return 1
if __name__=='__main__':
    text=msg(); print('Telegram message preview:'); print(text[:1200]); raise SystemExit(send(text))
