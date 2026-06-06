#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone, timedelta
import csv, os, urllib.parse, urllib.request
KST=timezone(timedelta(hours=9))
def now(): return datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')
def read(p,n=100):
    if not Path(p).exists(): return []
    for enc in ('utf-8-sig','utf-8','cp949','euc-kr'):
        try:
            with open(p,encoding=enc,newline='') as f: return list(csv.DictReader(f))[:n]
        except Exception: pass
    return []
def pick(r,names):
    lm={str(k).lower():k for k in r.keys()}
    for x in names:
        if x.lower() in lm: return str(r.get(lm[x.lower()],'')).strip()
    for k,v in r.items():
        if any(x.lower() in str(k).lower() for x in names): return str(v).strip()
    return ''
def status():
    d={}
    for r in read('docs/data/latest_publish_status.csv',20):
        if r.get('key'): d[r['key']]=r.get('value','')
    return d
def message():
    st=status(); ss=(st.get('session') or 'MANUAL').upper(); title='[장전 리포트 완료]' if ss=='AM' else '[장마감 리포트 완료]' if ss=='PM' else '[주식 리포트 완료]'
    h=read('docs/data/latest_holding_deep_analysis.csv'); counts={}
    for r in h:
        d=pick(r,['decision','판단']) or 'UNKNOWN'; counts[d]=counts.get(d,0)+1
    hold='보유종목 판단: '+(', '.join(f'{k} {v}개' for k,v in sorted(counts.items())) if counts else '데이터 확인 필요')
    return f"""{title}\n\n생성시각: {st.get('published_at') or now()}\n세션: {ss}\n\n{hold}\n\n모바일 홈:\nhttps://boxinmycat.github.io/stock-report/mobile/\n\n최신 리포트:\nhttps://boxinmycat.github.io/stock-report/latest/\n\n보유종목:\nhttps://boxinmycat.github.io/stock-report/v11_holdings/\n\n뉴스상세:\nhttps://boxinmycat.github.io/stock-report/details/naver_news.html\n"""
def main():
    token=os.environ.get('TELEGRAM_BOT_TOKEN','').strip(); chat=os.environ.get('TELEGRAM_CHAT_ID','').strip(); print('TELEGRAM_BOT_TOKEN:', 'OK' if token else 'MISSING'); print('TELEGRAM_CHAT_ID:', 'OK' if chat else 'MISSING')
    if not token or not chat: return 0
    data=urllib.parse.urlencode({'chat_id':chat,'text':message(),'disable_web_page_preview':'true'}).encode()
    with urllib.request.urlopen(f'https://api.telegram.org/bot{token}/sendMessage',data=data,timeout=15) as r: print('✅ Telegram alert sent'); print(r.read().decode(errors='ignore')[:300])
if __name__=='__main__': main()
