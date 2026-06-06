#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone, timedelta
import html, os, re
KST=timezone(timedelta(hours=9))
def now(): return datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')
def sess():
    e=(os.environ.get('REPORT_SESSION') or os.environ.get('SESSION') or '').strip().upper()
    if e in ('AM','PM','MANUAL'): return e
    h=datetime.now(KST).hour
    return 'AM' if h<12 else 'PM' if h<18 else 'MANUAL'
def k(p):
    m=re.search(r'(20\d{6})(?:[_-]?(AM|PM))?',p.parent.name,re.I)
    return (int(m.group(1)),{'AM':1,'PM':2}.get((m.group(2) or '').upper(),0),p.stat().st_mtime) if m else (0,0,p.stat().st_mtime)
def src():
    r=Path('docs/reports'); c=[p for p in r.rglob('index.html') if p.is_file()] if r.exists() else []
    if c: return max(c,key=k)
    p=Path('docs/index.html'); return p if p.exists() else None
def main():
    stamp,ss=now(),sess(); Path('docs/latest').mkdir(parents=True,exist_ok=True); out=Path('docs/latest/index.html'); s=src()
    if s:
        txt=s.read_text(encoding='utf-8',errors='ignore'); banner=f"<div style='margin:12px;padding:12px;border-radius:12px;background:#eef2ff;color:#1e1b4b'><b>Latest refreshed:</b> {html.escape(stamp)} / {html.escape(ss)}<br>source: {html.escape(s.as_posix())}</div>"
        i=txt.lower().find('<body')
        if i>=0 and txt.find('>',i)>=0:
            j=txt.find('>',i); txt=txt[:j+1]+banner+txt[j+1:]
        else: txt=banner+txt
        out.write_text(txt+f"\n<!-- latest-refresh:{stamp}/{ss}/source={s.as_posix()} -->\n",encoding='utf-8'); print(f'✅ latest refreshed from: {s}')
    else:
        out.write_text(f"<html><body><h1>Latest</h1><p>{stamp}</p><!-- latest-refresh:{stamp} --></body></html>",encoding='utf-8')
    Path('docs/mobile').mkdir(parents=True,exist_ok=True)
    links=[('최신 리포트','../latest/'),('보유종목','../v11_holdings/'),('전략검증','../strategy/'),('뉴스상세','../details/naver_news.html')]
    cards=''.join(f"<a class='card' href='{u}'><b>{t}</b><span>열기</span></a>" for t,u in links)
    Path('docs/mobile/index.html').write_text(f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><style>body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f6f7fb;margin:0}}.wrap{{max-width:860px;margin:auto;padding:20px}}.hero{{background:#111827;color:white;border-radius:22px;padding:22px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin-top:14px}}.card{{display:flex;justify-content:space-between;text-decoration:none;color:#111827;background:white;border-radius:18px;padding:18px;box-shadow:0 4px 16px #0001}}</style></head><body><main class='wrap'><section class='hero'><h1>주식 리포트 모바일 홈</h1><p>최근 갱신: {stamp}<br>세션: {ss}</p></section><section class='grid'>{cards}</section></main><!-- mobile-refresh:{stamp} --></body></html>""",encoding='utf-8')
    Path('docs/data').mkdir(parents=True,exist_ok=True); Path('docs/data/latest_publish_status.csv').write_text(f"key,value\npublished_at,{stamp}\nsession,{ss}\nsource,{s.as_posix() if s else 'not_found'}\n",encoding='utf-8-sig'); print('✅ latest publish status csv written')
if __name__=='__main__': main()
