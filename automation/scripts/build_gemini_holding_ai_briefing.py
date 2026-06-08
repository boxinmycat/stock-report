#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone, timedelta
import html, json, os, re, time, urllib.parse, urllib.request, urllib.error
import pandas as pd
KST=timezone(timedelta(hours=9))
def now(): return datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')
def read(p):
    p=Path(p)
    if not p.exists(): return pd.DataFrame()
    for e in ('utf-8-sig','utf-8','cp949','euc-kr'):
        try: return pd.read_csv(p,dtype=str,encoding=e).fillna('')
        except Exception: pass
    return pd.DataFrame()
def write(df,p): p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); df.fillna('').to_csv(p,index=False,encoding='utf-8-sig')
def s(x):
    v=str(x).strip() if x is not None else ''
    return '' if v.lower() in ('nan','none','null') else v
def get(row,*names):
    for n in names:
        if n in row and s(row.get(n)): return s(row.get(n))
    low={str(k).lower():k for k in row.keys()}
    for n in names:
        k=low.get(n.lower())
        if k and s(row.get(k)): return s(row.get(k))
    return ''
def clean(x): return re.sub(r'<.*?>','',html.unescape(s(x)))
def related(news,name,limit=5):
    if news.empty or not name: return []
    rows=[]; toks=[t for t in re.split(r'[\s/·,_-]+',name) if len(t)>=3]
    for _,r in news.iterrows():
        txt=' '.join([get(r,'query','검색어'),clean(get(r,'title','제목')),clean(get(r,'description','요약','본문'))]); score=0
        if get(r,'query','검색어')==name: score+=10
        if name in txt: score+=6
        score += sum(1 for t in toks if t in txt)
        if score>0: rows.append((score,{'title':clean(get(r,'title','제목')) or '제목 없음','description':clean(get(r,'description','요약','본문')),'link':get(r,'link','링크'),'pubDate':get(r,'pubDate','날짜')}))
    rows.sort(key=lambda x:x[0],reverse=True)
    return [x[1] for x in rows[:limit]]
def fallback(name,decision,pnl,links):
    issue = f"{name} 관련 뉴스 {len(links)}건을 기준으로 점검했습니다. Gemini API가 없거나 호출에 실패해 규칙 기반 요약으로 표시합니다."
    if links: issue += ' 주요 기사: ' + ' / '.join(x['title'] for x in links[:2])
    return {'ai_status':'fallback_rule','ai_sentiment':'중립','ai_confidence':'낮음','ai_issue_summary':issue,'ai_positive_points':'AI 해석 실패로 긍정 포인트는 기사 제목과 기존 리포트를 함께 확인해야 합니다.','ai_risk_points':'AI 해석 실패 상태이므로 손절가와 현재가 매칭 상태를 우선 확인하세요.','ai_price_context':f'현재 손익률은 {pnl or "계산 대기"}이고 현재 판단은 {decision or "대기"}입니다.','ai_action_guide':'자동 해석이 불완전하므로 신규 매수/추가매수보다 보유 기준, 목표가, 손절가를 먼저 확인하세요.','ai_three_line_summary':'1. AI 브리핑은 fallback 상태입니다.\n2. 뉴스 링크와 현재가를 직접 확인하세요.\n3. 손절가 아래 물타기는 피하는 기준이 좋습니다.','ai_caution':'투자 판단 보조용이며 매수·매도 확정 지시가 아닙니다.'}
def extract_json(text):
    text=text.strip(); text=re.sub(r'^```(?:json)?\s*','',text); text=re.sub(r'\s*```$','',text)
    m=re.search(r'\{.*\}',text,re.S)
    if m: text=m.group(0)
    return json.loads(text)
def call_gemini(prompt):
    key=os.environ.get('GEMINI_API_KEY','').strip()
    primary=os.environ.get('GEMINI_MODEL','gemini-3.5-flash').strip() or 'gemini-3.5-flash'
    models=[]
    for m in [primary, 'gemini-2.5-flash', 'gemini-2.5-flash-lite']:
        if m and m not in models:
            models.append(m)
    if not key:
        raise RuntimeError('GEMINI_API_KEY missing')
    last_error=None
    for model in models:
        try:
            url=f'https://generativelanguage.googleapis.com/v1beta/models/{urllib.parse.quote(model)}:generateContent'
            payload={'system_instruction':{'parts':[{'text':'당신은 한국 주식 보유자를 위한 신중한 리서치 보조자입니다. 투자 권유나 확정적 매수/매도 지시를 하지 말고, 뉴스 맥락·가격 상태·리스크를 균형 있게 요약하세요. 반드시 JSON만 출력하세요.'}]},'contents':[{'parts':[{'text':prompt}]}],'generationConfig':{'temperature':0.25,'maxOutputTokens':1200,'responseMimeType':'application/json'}}
            req=urllib.request.Request(url,data=json.dumps(payload,ensure_ascii=False).encode('utf-8'),headers={'Content-Type':'application/json','x-goog-api-key':key})
            with urllib.request.urlopen(req,timeout=35) as res:
                data=json.loads(res.read().decode('utf-8'))
            txt=data.get('candidates',[{}])[0].get('content',{}).get('parts',[{}])[0].get('text','')
            if not txt:
                raise RuntimeError('empty Gemini response')
            out=extract_json(txt)
            out['gemini_model_used']=model
            return out
        except Exception as e:
            last_error=e
            print(f'⚠️ Gemini model failed: {model} :: {repr(e)}')
    raise RuntimeError(f'all Gemini models failed: {repr(last_error)}')

def prompt_for(h,links):
    news='\n'.join([f"[{i+1}] 제목: {x['title']}\n요약: {x['description']}\n링크: {x['link']}" for i,x in enumerate(links)]) or '관련 뉴스 없음'
    return f"""
아래는 사용자의 실제 보유종목 데이터와 최근 네이버뉴스입니다.
종목명: {get(h,'stock_name','종목명')}
종목코드: {get(h,'stock_code','종목코드')}
현재 판단: {get(h,'decision','판단')}
현재가: {get(h,'current_price','현재가')}
평균단가: {get(h,'avg_price','평균단가')}
손익률(%): {get(h,'unrealized_pnl_pct','손익률')}
목표가: {get(h,'target_price','목표가')}
손절가: {get(h,'stop_loss','손절가')}
현재가 출처: {get(h,'current_price_source','price_source')}

뉴스 목록:
{news}

다음 JSON 형식으로만 답하세요.
{{
  "ai_sentiment": "긍정|중립|주의|위험",
  "ai_confidence": "높음|보통|낮음",
  "ai_issue_summary": "현재 이슈 흐름을 4~6문장으로 상세 설명",
  "ai_positive_points": "긍정 포인트를 3~5문장으로 설명",
  "ai_risk_points": "리스크 포인트를 3~5문장으로 설명",
  "ai_price_context": "현재가, 평균단가, 손익률을 연결한 해석 3~5문장",
  "ai_action_guide": "보유자 관점 대응 가이드 4~6문장. 매수/매도 확정 지시는 금지",
  "ai_three_line_summary": "1. ...\\n2. ...\\n3. ...",
  "ai_caution": "투자 판단 보조용 주의문"
}}
""".strip()
def build():
    holdings=read('docs/data/latest_holding_deep_analysis.csv'); news=read('docs/data/latest_news_detail.csv')
    rows=[]; cards=''
    if holdings.empty:
        write(pd.DataFrame([{'ai_status':'NO_HOLDINGS','message':'보유종목 데이터 없음','checked_at':now()}]),'docs/data/latest_holding_ai_briefing.csv'); return
    for _,h in holdings.iterrows():
        name=get(h,'stock_name','종목명'); dec=get(h,'decision','판단'); pnl=get(h,'unrealized_pnl_pct','손익률'); links=related(news,name,5)
        try:
            out=call_gemini(prompt_for(h,links)); out['ai_status']='gemini_ok'
        except Exception as e:
            out=fallback(name,dec,pnl,links); out['ai_error']=repr(e)
        row={'stock_name':name,'stock_code':get(h,'stock_code','종목코드'),'decision':dec,'current_price':get(h,'current_price','현재가'),'avg_price':get(h,'avg_price','평균단가'),'pnl_pct':pnl,'price_source':get(h,'current_price_source','price_source'),'checked_at':now(),**out}
        for i,x in enumerate(links,1):
            row[f'news_title_{i}']=x['title']; row[f'news_link_{i}']=x['link']; row[f'news_desc_{i}']=x['description']
        rows.append(row); time.sleep(0.2)
        news_li=''.join([f"<li><b>{html.escape(x['title'])}</b><br><span>{html.escape(x['description'][:220])}</span><br>{('<a href="'+html.escape(x['link'])+'" target="_blank" rel="noopener">기사 보기</a>') if x['link'] else ''}</li>" for x in links]) or '<li>연결된 상세 뉴스가 충분하지 않습니다.</li>'
        cards += f"""<article class='card'><div class='head'><h2>{html.escape(name)}</h2><span>{html.escape(out.get('ai_sentiment','중립'))} · {html.escape(out.get('ai_confidence',''))}</span></div><div class='meta'>판단 {html.escape(dec)} · 현재가 {html.escape(row['current_price'])} · 평균단가 {html.escape(row['avg_price'])} · 손익률 {html.escape(pnl)}% · AI상태 {html.escape(out.get('ai_status',''))}</div><section><h3>AI 이슈 브리핑</h3><p>{html.escape(out.get('ai_issue_summary',''))}</p></section><section><h3>긍정 포인트</h3><p>{html.escape(out.get('ai_positive_points',''))}</p></section><section><h3>리스크 포인트</h3><p>{html.escape(out.get('ai_risk_points',''))}</p></section><section><h3>가격·보유 관점</h3><p>{html.escape(out.get('ai_price_context',''))}</p></section><section><h3>대응 가이드</h3><p>{html.escape(out.get('ai_action_guide',''))}</p></section><section><h3>3줄 요약</h3><pre>{html.escape(out.get('ai_three_line_summary',''))}</pre></section><section><h3>관련 뉴스 링크</h3><ul>{news_li}</ul></section><p class='caution'>{html.escape(out.get('ai_caution','투자 판단 보조용입니다.'))}</p></article>"""
    df=pd.DataFrame(rows); write(df,'docs/data/latest_holding_ai_briefing.csv'); write(df,'docs/data/latest_holding_issue_analysis.csv')
    Path('docs/details').mkdir(parents=True,exist_ok=True)
    page=f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Gemini AI 보유종목 브리핑</title><style>body{{margin:0;background:#f6f7fb;color:#111827;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}.wrap{{max-width:980px;margin:auto;padding:20px}}.hero{{background:#1f2937;color:white;border-radius:22px;padding:22px;margin-bottom:16px}}.hero p{{color:#d1d5db;line-height:1.55}}.card{{background:white;border-radius:20px;padding:18px;margin-bottom:16px;box-shadow:0 4px 16px #0001}}.head{{display:flex;justify-content:space-between;gap:12px;align-items:center;border-bottom:1px solid #e5e7eb;padding-bottom:10px;margin-bottom:12px}}.head h2{{margin:0;font-size:21px}}.head span{{background:#eef2ff;color:#3730a3;border-radius:999px;padding:6px 10px;font-weight:700;font-size:12px}}.meta{{font-size:13px;color:#6b7280;margin-bottom:14px;line-height:1.5}}section{{margin:14px 0}}h3{{font-size:15px;margin:0 0 6px}}p,li{{font-size:14px;line-height:1.72;color:#374151}}pre{{white-space:pre-wrap;background:#f9fafb;border-radius:12px;padding:12px;font-size:14px;line-height:1.6}}a{{color:#2563eb;font-weight:700;text-decoration:none}}.caution{{font-size:12px;color:#6b7280;border-top:1px solid #e5e7eb;padding-top:10px}}</style></head><body><main class='wrap'><section class='hero'><h1>Gemini AI 보유종목 브리핑</h1><p>갱신: {html.escape(now())}<br>보유종목 현재가와 네이버뉴스를 Gemini가 해석한 브리핑입니다. 매수·매도 확정 지시가 아니라 판단 보조 자료입니다.</p></section>{cards}</main></body></html>"""
    Path('docs/details/holding_ai_briefing.html').write_text(page,encoding='utf-8'); Path('docs/details/holding_issues.html').write_text(page,encoding='utf-8')
    print('✅ Gemini holding AI briefing built'); print(f'rows: {len(rows)}')
if __name__=='__main__': build()
