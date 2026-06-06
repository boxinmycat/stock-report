#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone, timedelta
import html, os, re
KST=timezone(timedelta(hours=9))
def now(): return datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')
def session():
    v=(os.getenv('REPORT_SESSION') or os.getenv('SESSION') or '').upper().strip()
    if v in ('AM','PM','MANUAL'): return v
    h=datetime.now(KST).hour
    return 'AM' if h<12 else 'PM' if h<18 else 'MANUAL'
def key(p):
    m=re.search(r'(20\d{6})(?:[_-]?(AM|PM))?', p.parent.name, re.I)
    if m: return (int(m.group(1)), {'AM':1,'PM':2}.get((m.group(2) or '').upper(),0), p.stat().st_mtime)
    return (0,0,p.stat().st_mtime)
def latest_source():
    c=[]
    r=Path('docs/reports')
    if r.exists(): c=[p for p in r.rglob('index.html') if p.is_file()]
    if c: return max(c,key=key)
    p=Path('docs/index.html')
    return p if p.exists() else None
def rel_from_latest(p):
    try: return '../'+p.relative_to(Path('docs')).as_posix()
    except Exception: return '../index.html'
def mobile(stamp,sess):
    d=Path('docs/mobile'); d.mkdir(parents=True,exist_ok=True)
    links=[('최신 리포트','../latest/'),('v11 보유종목','../v11_holdings/'),('전략검증','../strategy/'),('상세 데이터','../details/'),('네이버뉴스 상세','../details/naver_news.html')]
    cards=''.join(f'<a class="card" href="{html.escape(u)}"><b>{html.escape(t)}</b><span>열기</span></a>' for t,u in links)
    (d/'index.html').write_text(f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Stock Report Mobile</title><style>body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f6f7fb;margin:0;color:#111827}}.wrap{{max-width:860px;margin:0 auto;padding:20px}}.hero{{background:#111827;color:white;border-radius:22px;padding:22px;margin-bottom:16px}}.meta{{color:#d1d5db;font-size:14px;line-height:1.6}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}}.card{{display:flex;justify-content:space-between;text-decoration:none;background:white;color:#111827;border-radius:18px;padding:18px;box-shadow:0 4px 16px rgba(0,0,0,.06)}}.card span{{color:#2563eb;font-weight:700}}</style></head><body><main class="wrap"><section class="hero"><h1>주식 리포트 모바일 홈</h1><div class="meta">최근 갱신: {html.escape(stamp)}<br>세션: {html.escape(sess)}</div></section><section class="grid">{cards}</section></main><!-- mobile-refresh:{html.escape(stamp)} --></body></html>''',encoding='utf-8')
    print('✅ mobile page refreshed: docs/mobile/index.html')
def main():
    stamp=now(); sess=session(); out=Path('docs/latest/index.html'); out.parent.mkdir(parents=True,exist_ok=True)
    src=latest_source()
    if src:
        text=src.read_text(encoding='utf-8',errors='ignore')
        banner=f'<div style="margin:12px 0;padding:12px;border-radius:12px;background:#eef2ff;color:#1e1b4b;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;font-size:14px"><b>Latest page refreshed:</b> {html.escape(stamp)} / {html.escape(sess)}<br>source: <a href="{html.escape(rel_from_latest(src))}">{html.escape(src.as_posix())}</a></div>'
        i=text.lower().find('<body')
        if i>=0:
            j=text.find('>',i); text=text[:j+1]+banner+text[j+1:] if j>=0 else banner+text
        else: text=banner+text
        text += f'\n<!-- latest-refresh: {stamp} / {sess} / source={src.as_posix()} -->\n'
        out.write_text(text,encoding='utf-8')
        print('✅ latest refreshed from:',src)
    else:
        out.write_text(f'<!doctype html><html><body><h1>Latest Stock Report</h1><p>{stamp}</p><!-- fallback --></body></html>',encoding='utf-8')
        print('⚠️ report index not found; fallback latest page created')
    mobile(stamp,sess)
    data=Path('docs/data'); data.mkdir(parents=True,exist_ok=True)
    (data/'latest_publish_status.csv').write_text('key,value\n'+f'published_at,{stamp}\nsession,{sess}\nlatest_file,docs/latest/index.html\nsource,{src.as_posix() if src else "not_found"}\n',encoding='utf-8-sig')
    print('✅ latest publish status csv written')
if __name__=='__main__': main()
