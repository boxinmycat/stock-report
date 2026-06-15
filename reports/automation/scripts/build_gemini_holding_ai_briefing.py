#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# v12.2.23 holding AI news quality hotfix
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone, timedelta
import html, json, os, re, time, urllib.parse, urllib.request, urllib.error
import pandas as pd

try:
    from stock_news_disambiguation import filter_and_rank_news, extract_publisher, format_pubdate, news_quality_score
except Exception:
    filter_and_rank_news = None
    extract_publisher = lambda link='', originallink='', raw='': ''
    format_pubdate = lambda value: str(value or '')
    news_quality_score = lambda title, description='', pubDate='', publisher='', link='', originallink='': (0, 'fallback')
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
NEWS_BLACKLIST={'태웅':['태웅식품','태웅로직스','태웅푸드']}

def _local_news_quality_score(title, description='', pubDate='', publisher='', link='', originallink=''):
    text = f"{title or ''} {description or ''}"
    score = 0
    reason = []
    important = ['실적','영업이익','매출','공시','수주','계약','유상증자','자사주','배당','대주주','목표가','투자의견','수출','해외']
    low = ['주가','마감','장중','상승 마감','하락 마감','급등','급락','강세','약세']
    imp = sum(1 for w in important if w in text)
    lw = sum(1 for w in low if w in str(title or ''))
    score += min(imp * 2, 10)
    if imp:
        reason.append(f'important:{imp}')
    if lw and not imp:
        score -= min(lw * 2, 6)
        reason.append(f'price_only:{lw}')
    if re.search(r"\d{1,2}월\s*\d{1,2}일", str(title or '')) and ('마감' in str(title or '') or '%' in str(title or '')) and not imp:
        score -= 5
        reason.append('dated_price_close_article')
    return score, ','.join(reason) or 'local_fallback'

try:
    news_quality_score
except NameError:
    news_quality_score = _local_news_quality_score

def strict_stock_news_match(text,name):
    if not name or name not in text: return False
    if any(bad in text for bad in NEWS_BLACKLIST.get(name,[])): return False
    for suffix in ['식품','푸드','로직스','바이오','제약']:
        if len(name)<=3 and name+suffix in text: return False
    return True
def related(news,name,limit=5):
    if news.empty or not name: return []
    rows = [dict(r) for _, r in news.iterrows()]
    if filter_and_rank_news:
        ranked = filter_and_rank_news(name, '', rows, limit=limit)
    else:
        ranked = rows[:limit]
    out=[]
    for r in ranked[:limit]:
        title=clean(get(r,'title','제목')) or '제목 없음'
        desc=clean(get(r,'description','요약','본문'))
        link=get(r,'link','링크')
        pub=get(r,'published_at') or format_pubdate(get(r,'pubDate','날짜'))
        press=get(r,'publisher') or extract_publisher(link, get(r,'originallink','origin_link'))
        qscore,qreason = news_quality_score(title, desc, get(r,'pubDate','날짜'), press, link, get(r,'originallink','origin_link'))
        out.append({'title':title,'description':desc,'link':link,'pubDate':get(r,'pubDate','날짜'),'published_at':pub,'publisher':press,'news_quality_score':qscore,'news_quality_reason':qreason})
    return out

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
            payload={'system_instruction':{'parts':[{'text':'당신은 한국 주식 보유자를 위한 직설적 리서치 보조자입니다. 모호한 격언을 피하고, 가능한 경우 날짜·현재가·평균단가·손익률·손절가·목표가를 기준으로 판단하세요. 확정적 매수/매도 명령은 피하되, 보유자 관점에서 보유/부분정리/손절검토/추가매수보류/회복확인 같은 명확한 대응 방향을 제시하세요. 반드시 JSON만 출력하세요.'}]},'contents':[{'parts':[{'text':prompt}]}],'generationConfig':{'temperature':0.25,'maxOutputTokens':1200,'responseMimeType':'application/json'}}
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
    news_lines=[]
    for i,x in enumerate(links):
        press = x.get('publisher') or ''
        published = x.get('published_at') or x.get('pubDate') or ''
        qscore = x.get('news_quality_score') or ''
        news_lines.append(
            f"[{i+1}] {press} / {published} / 품질점수 {qscore}\n"
            f"제목: {x.get('title','')}\n"
            f"요약: {x.get('description','')}\n"
            f"링크: {x.get('link','')}"
        )
    news='\n\n'.join(news_lines) or '관련 뉴스 없음'
    return f"""
아래는 사용자의 실제 보유종목 데이터와 최근 뉴스입니다.
평이한 투자 격언은 쓰지 말고, 사용자가 지금 보유 중인 종목을 어떻게 해석해야 하는지 명확히 알려주세요.

종목명: {get(h,'stock_name','종목명')}
종목코드: {get(h,'stock_code','종목코드')}
현재 판단: {get(h,'decision','판단')}
현재가: {get(h,'current_price','현재가')}
평균단가: {get(h,'avg_price','평균단가')}
손익률(%): {get(h,'unrealized_pnl_pct','손익률')}
목표가: {get(h,'target_price','목표가')}
손절가: {get(h,'stop_loss','손절가')}
현재가 출처: {get(h,'current_price_source','price_source')}
브리핑 기준일: {now()}

뉴스 목록:
{news}

작성 원칙:
- "신중하게 대응", "지켜볼 필요" 같은 모호한 표현만으로 끝내지 마세요.
- 현재가, 평균단가, 손익률, 손절가, 목표가가 있으면 반드시 해석에 반영하세요.
- 가능하면 "언제/어느 가격대에서 일부 정리했어야 했는지", "지금은 추가매수 보류인지", "손절 검토 가격은 어디인지"를 말하세요.
- 뉴스가 오래되었거나 단순 주가마감 기사라면 영향도가 낮다고 판단하세요.
- 보유자의 궁금증은 "그래서 지금 이 주식을 어떻게 해야 하나?"입니다.

다음 JSON 형식으로만 답하세요.
{{
  "ai_sentiment": "긍정|중립|주의|위험",
  "ai_confidence": "높음|보통|낮음",
  "ai_issue_summary": "현재 이슈 흐름을 4~7문장으로 설명. 단순 뉴스 나열 금지",
  "ai_positive_points": "긍정 포인트를 종목 특성에 맞춰 3~5문장으로 설명",
  "ai_risk_points": "리스크 포인트를 가격·재무·수급·뉴스 품질과 연결해 3~5문장으로 설명",
  "ai_price_context": "현재가, 평균단가, 손익률, 손절가/목표가를 연결한 해석. 숫자 중심으로 3~5문장",
  "ai_action_guide": "현재 대응을 4~6문장으로 명확히 제시. 보유/부분정리/손절검토/추가매수보류/회복확인 등의 표현을 사용",
  "ai_retrospective": "이 종목은 어느 구간에서 팔았어야 했는지, 또는 아직 기다릴 근거가 있는지 사후 복기 2~4문장",
  "ai_three_line_summary": "1. 이슈와 가능성 판단\n2. 평균단가 대비 손익률과 가격 기준\n3. 지금 대응 방향",
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
            row[f'news_title_{i}']=x['title']; row[f'news_link_{i}']=x['link']; row[f'news_desc_{i}']=x['description']; row[f'news_publisher_{i}']=x.get('publisher',''); row[f'news_published_at_{i}']=x.get('published_at',''); row[f'news_quality_score_{i}']=x.get('news_quality_score','')
        rows.append(row)
        time.sleep(0.2)
        news_items = []
        for x in links:
            title_html = html.escape(str(x.get('title', '')))
            desc_html = html.escape(str(x.get('description', ''))[:220])
            meta_html = html.escape(' · '.join([v for v in [str(x.get('publisher','')), str(x.get('published_at','')), ('품질 '+str(x.get('news_quality_score',''))) if str(x.get('news_quality_score','')) else ''] if v]))
            link = str(x.get('link', '') or '').strip()
            if link:
                link_html = f'<a href="{html.escape(link)}" target="_blank" rel="noopener">기사 보기</a>'
            else:
                link_html = ''
            news_items.append(
                '<li>'
                f'<small class="newsmeta">{meta_html}</small><br>'
                f'<b>{title_html}</b><br>'
                f'<span>{desc_html}</span><br>'
                f'{link_html}'
                '</li>'
            )
        news_li = ''.join(news_items) or '<li>연결된 상세 뉴스가 충분하지 않습니다.</li>'
        cards += f"""<article class='card'><div class='head'><h2>{html.escape(name)}</h2><span>{html.escape(out.get('ai_sentiment','중립'))} · {html.escape(out.get('ai_confidence',''))}</span></div><div class='meta'>판단 {html.escape(dec)} · 현재가 {html.escape(row['current_price'])} · 평균단가 {html.escape(row['avg_price'])} · 손익률 {html.escape(pnl)}% · AI상태 {html.escape(out.get('ai_status',''))}</div><section><h3>AI 이슈 브리핑</h3><p>{html.escape(out.get('ai_issue_summary',''))}</p></section><section><h3>긍정 포인트</h3><p>{html.escape(out.get('ai_positive_points',''))}</p></section><section><h3>리스크 포인트</h3><p>{html.escape(out.get('ai_risk_points',''))}</p></section><section><h3>가격·보유 관점</h3><p>{html.escape(out.get('ai_price_context',''))}</p></section><section><h3>대응 가이드</h3><p>{html.escape(out.get('ai_action_guide',''))}</p></section><section><h3>직전 판단/매도 복기</h3><p>{html.escape(out.get('ai_retrospective',''))}</p></section><section><h3>3줄 요약</h3><pre>{html.escape(out.get('ai_three_line_summary',''))}</pre></section><section><h3>관련 뉴스 링크</h3><ul>{news_li}</ul></section><p class='caution'>{html.escape(out.get('ai_caution','투자 판단 보조용입니다.'))}</p></article>"""
    df=pd.DataFrame(rows); write(df,'docs/data/latest_holding_ai_briefing.csv'); write(df,'docs/data/latest_holding_issue_analysis.csv')
    Path('docs/details').mkdir(parents=True,exist_ok=True)
    page=f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Gemini AI 보유종목 브리핑</title><style>body{{margin:0;background:#f6f7fb;color:#111827;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}.wrap{{max-width:980px;margin:auto;padding:20px}}.hero{{background:#1f2937;color:white;border-radius:22px;padding:22px;margin-bottom:16px}}.hero p{{color:#d1d5db;line-height:1.55}}.card{{background:white;border-radius:20px;padding:18px;margin-bottom:16px;box-shadow:0 4px 16px #0001}}.head{{display:flex;justify-content:space-between;gap:12px;align-items:center;border-bottom:1px solid #e5e7eb;padding-bottom:10px;margin-bottom:12px}}.head h2{{margin:0;font-size:21px}}.head span{{background:#eef2ff;color:#3730a3;border-radius:999px;padding:6px 10px;font-weight:700;font-size:12px}}.meta{{font-size:13px;color:#6b7280;margin-bottom:14px;line-height:1.5}}section{{margin:14px 0}}h3{{font-size:15px;margin:0 0 6px}}p,li{{font-size:14px;line-height:1.72;color:#374151}}pre{{white-space:pre-wrap;background:#f9fafb;border-radius:12px;padding:12px;font-size:14px;line-height:1.6}}a{{color:#2563eb;font-weight:700;text-decoration:none}}.caution{{font-size:12px;color:#6b7280;border-top:1px solid #e5e7eb;padding-top:10px}}.newsmeta{{font-size:12px;color:#6b7280}}</style></head><body><main class='wrap'><section class='hero'><h1>Gemini AI 보유종목 브리핑</h1><p>갱신: {html.escape(now())}<br>보유종목 현재가와 네이버뉴스를 Gemini가 해석한 브리핑입니다. 매수·매도 확정 지시가 아니라 판단 보조 자료입니다.</p></section>{cards}</main></body></html>"""
    Path('docs/details/holding_ai_briefing.html').write_text(page,encoding='utf-8'); Path('docs/details/holding_issues.html').write_text(page,encoding='utf-8')
    print('✅ Gemini holding AI briefing built'); print(f'rows: {len(rows)}')
if __name__=='__main__': build()
