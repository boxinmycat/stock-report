#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone, timedelta
import html, json, os, re, time, urllib.parse, urllib.request, urllib.error
import pandas as pd

BANNED_MANAGER_PHRASES = [
    "신중하게 접근", "신중히 접근", "관찰이 요망", "추이를 관찰", "지켜봐야", "주의가 필요", "신중한 대응"
]

def clean_manager_text(value: str) -> str:
    text = str(value or "")
    for phrase in BANNED_MANAGER_PHRASES:
        text = text.replace(phrase, "정량적 매매 가이드라인 기반 기계적 대응")
    return text.strip()

try:
    from stock_news_disambiguation import filter_and_rank_news, extract_publisher, format_pubdate, news_quality_score
except Exception:
    filter_and_rank_news = None
    extract_publisher = lambda link='', originallink='', raw='': '주요언론사'
    format_pubdate = lambda value: str(value or '')
    news_quality_score = lambda title, description='', pubDate='', publisher='', link='', originallink='': (50, 'fallback')

KST = timezone(timedelta(hours=9))
def now(): return datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')

def read(p):
    p = Path(p)
    if not p.exists(): return pd.DataFrame()
    for e in ('utf-8-sig','utf-8','cp949','euc-kr'):
        try: return pd.read_csv(p,dtype=str,encoding=e).fillna('')
        except Exception: pass
    return pd.DataFrame()

def write(df,p): 
    p = Path(p); p.parent.mkdir(parents=True,exist_ok=True); df.fillna('').to_csv(p,index=False,encoding='utf-8-sig')

def s(x):
    v = str(x).strip() if x is not None else ''
    return '' if v.lower() in ('nan','none','null') else v

def get(row,*names):
    for n in names:
        if n in row and s(row.get(n)): return s(row.get(n))
    low = {str(k).lower():k for k in row.keys()}
    for n in names:
        k = low.get(n.lower())
        if k and s(row.get(k)): return s(row.get(k))
    return ''

def clean(x): return re.sub(r'<.*?>','',html.unescape(s(x)))
ACTIONS = ['보유 유지','부분 정리','손절 검토','추가 매수 보류','원금 회복 확인','반등 시 축소']

def related(news,name,limit=3):
    if news.empty or not name: return []
    rows = [dict(r) for _, r in news.iterrows()]
    if filter_and_rank_news:
        ranked = filter_and_rank_news(name, '', rows, limit=limit)
    else:
        ranked = rows[:limit]
    out = []
    for r in ranked[:limit]:
        title = clean(get(r,'title','제목'))
        desc = clean(get(r,'description','요약','본문'))
        link = get(r,'link','링크')
        pub = get(r['pubDate']) if get(r,'pubDate') else (get(r,'published_at') or '')
        press = get(r,'publisher') or extract_publisher(link, get(r,'originallink','origin_link'))
        qscore, qreason = news_quality_score(title, desc, pub, press, link, get(r,'originallink','origin_link'))
        out.append({'title':title,'description':desc,'link':link,'pubDate':pub,'published_at':pub,'publisher':press,'news_quality_score':qscore,'news_quality_reason':qreason})
    return out

def practical_action(h):
    pnl = None
    try: pnl = float(re.sub(r'[^0-9.\-]', '', get(h,'unrealized_pnl_pct','손익률')) or 'nan')
    except: pnl = None
    decision = get(h,'decision','판단')
    if decision in ('🚨 손절검토','PRICE_NOT_MATCHED','STOP_WATCH'): return '손절 검토'
    if pnl is not None:
        if pnl <= -7: return '손절 검토'
        if pnl <= -3: return '추가 매수 보류'
        if pnl >= 8: return '부분 정리'
        if -1.5 <= pnl <= 1.5: return '원금 회복 확인'
    return '보유 유지'

def extract_json(text):
    text = text.strip().replace("```json", "").replace("```", "")
    m = re.search(r'\{.*\}', text, re.S)
    if m: text = m.group(0)
    return json.loads(text)

def call_gemini(prompt):
    key = os.environ.get('GEMINI_API_KEY','').strip()
    primary = os.environ.get('GEMINI_MODEL','gemini-1.5-flash').strip() or 'gemini-1.5-flash'
    if not key: raise RuntimeError('GEMINI_API_KEY missing')
    
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{urllib.parse.quote(primary)}:generateContent'
    payload = {
        'system_instruction': {
            'parts': [{
                'text': "당신은 냉철한 계좌 사수용 포트폴리오 책임 매니저입니다. '신중 관찰', '지켜봐야' 같은 면피조 문장을 작성 시 즉시 자격이 박탈됩니다. 무조건 요구된 구조의 JSON 데이터 단 한 장만 반환하십시오."
            }]
        },
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {'temperature': 0.15, 'maxOutputTokens': 1200, 'responseMimeType': 'application/json'}
    }
    req = urllib.request.Request(url, data=json.dumps(payload, ensure_ascii=False).encode('utf-8'), headers={'Content-Type': 'application/json', 'x-goog-api-key': key})
    with urllib.request.urlopen(req, timeout=35) as res:
        data = json.loads(res.read().decode('utf-8'))
    txt = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
    return extract_json(txt)

def prompt_for(h, links):
    news_lines = []
    for i, x in enumerate(links):
        news_lines.append(f"[{i+1}] {x.get('publisher','')} / 제목: {x.get('title','')}\n요약: {x.get('description','')}")
    news_text = '\n\n'.join(news_lines) or '특이 공시 관련 뉴스 없음.'
    
    return f"""
    보유 종목명: {get(h,'stock_name','종목명')}
    장부상 실시간 손익률: {get(h,'unrealized_pnl_pct','손익률')}%
    계량 규칙단 판단: {get(h,'decision','판단')}
    수집된 최근 뉴스 정보:
    {news_text}

    [엄격한 출력 준수 제약 조항]
    - 모호하고 원론적인 멘트를 전면 차단하십시오.
    - 아래 5대 서식 키에 맞춰 명확하고 꽉 찬 콘텐츠를 JSON 문자열로 출력하십시오.
    
    템플릿 서식 맵:
    {{
      "ai_action_headline": "보유 유지 / 부분 정리 / 손절 검토 / 추가 매수 보류 / 원금 회복 확인 / 반등 시 축소 중 평단 대비 실전 액션 택1",
      "ai_sentiment": "긍정 / 중립 / 주의 / 위험 중 택1",
      "ai_stock_explanation": "해당 주식의 핵심 BM 비즈니스 구조와 주가 주도 테마의 핵심을 명확히 2줄 요약 기술",
      "ai_positive_risk_points": "긍정포인트 호재 팩트 1가지와 리스크포인트 악재 위협 요인 1가지를 명확히 분리 대조 기술",
      "ai_price_action_guide": "장부의 평균단가와 실시간 현재가, 손절선 수치를 반영하여 기계적으로 대응할 수 있는 탈출 가격대와 매매 비중 가이드 지시",
      "ai_three_line_summary": "1. 첫번째 실전 핵심 요약\\n2. 두번째 실전 핵심 요약\\n3. 세번째 실전 핵심 요약",
      "ai_related_news_comment": "수집 뉴스 중 단순 시세를 제외한 실질 펀더멘탈 기사 최대 2~3개의 실제 영향력 평가 요약"
    }}
    """.strip()

def build():
    holdings = read('docs/data/latest_holding_deep_analysis.csv')
    news = read('docs/data/latest_news_detail.csv')
    rows = []; cards = ''
    if holdings.empty: return

    for _, h in holdings.iterrows():
        name = get(h,'stock_name','종목명')
        dec = get(h,'decision','판단')
        pnl = get(h,'unrealized_pnl_pct','손익률')
        links = related(news, name, 3)
        
        try:
            out = call_gemini(prompt_for(h, links))
            out['ai_status'] = 'gemini_ok'
        except:
            out = {"ai_action_headline": practical_action(h), "ai_sentiment": "중립", "ai_stock_explanation": "실시간 API 쿼리 한도 초과", "ai_positive_risk_points": "장부 가격 기준선을 참조하세요.", "ai_price_action_guide": "손절가 가이드라인에 입각해 대응하세요.", "ai_three_line_summary": "1. 동기화 버퍼 초과\n2. 장부 단가 기준 기계적 매매\n3. 물타기 전면 금지", "ai_related_news_comment": "생략", "ai_status": "fallback"}
            
        headline = clean_manager_text(out.get('ai_action_headline') or practical_action(h))
        expl = clean_manager_text(out.get('ai_stock_explanation') or '')
        points = clean_manager_text(out.get('ai_positive_risk_points') or '').replace('\n', '<br>')
        guide = clean_manager_text(out.get('ai_price_action_guide') or '')
        summary = clean_manager_text(out.get('ai_three_line_summary') or '').replace('\n', '<br>')
        comment = clean_manager_text(out.get('ai_related_news_comment') or '')

        row = {'stock_name': name, 'stock_code': get(h,'stock_code','종목코드'), 'decision': dec, 'current_price': get(h,'current_price','현재가'), 'avg_price': get(h,'avg_price','평균단가'), 'pnl_pct': pnl, 'ai_action_headline': headline, 'ai_three_line_summary': summary, 'checked_at': now()}
        rows.append(row)

        news_items = []
        for x in links[:3]:
            news_items.append(f"<li><b>[{html.escape(x.get('publisher','언론사'))}]</b> {html.escape(x.get('title',''))}</li>")
        news_li = ''.join(news_items) or '<li>연결된 실질 펀더멘탈 기사 없음.</li>'

        cards += f"""
        <article class="ai-brief-card">
            <div class="brief-card-head">
                <h2>{html.escape(name)} <small>({get(h,'stock_code','')})</small></h2>
                <span class="badge">{html.escape(headline)} · {out.get('ai_sentiment','중립')}</span>
            </div>
            <div class="meta-info">평단: {get(h,'avg_price','')}원 | 현재가: {get(h,'current_price','')}원 | 손익률: {pnl}%</div>
            <div class="step-box"><h3>1. 이 주식의 설명</h3><p>{html.escape(expl)}</p></div>
            <div class="step-box"><h3>2. 현재 이 주식, 회사의 긍정 포인트 / 리스크 포인트</h3><p>{points}</p></div>
            <div class="step-box"><h3>3. 가격&보유 관점과 향후 대응 가이드</h3><p style="color:#1e3a8a; font-weight:700;">{html.escape(guide)}</p></div>
            <div class="step-box"><h3>4. 3줄 요약</h3><div class="inner-summary">{summary}</div></div>
            <div class="step-box"><h3>5. 관련 뉴스 (최대 2~3개)</h3><p style="margin-bottom:6px; font-weight:600; color:#475569;">{html.escape(comment)}</p><ul>{news_li}</ul></div>
        </article>
        """

    write(pd.DataFrame(rows), 'docs/data/latest_holding_ai_briefing.csv')
    
    page = f"""<!doctype html>
    <html lang="ko">
    <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>보유종목 핵심 5단계 AI 브리핑</title>
    <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Malgun Gothic", sans-serif; background: #f3f4f6; margin: 0; padding: 12px; color: #0f172a; }}
    .container {{ max-width: 480px; margin: 0 auto; }}
    .banner {{ background: #1e3a8a; color: white; padding: 16px; border-radius: 16px; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
    .ai-brief-card {{ background: white; border-radius: 18px; padding: 14px; margin-bottom: 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.02); border-top: 4px solid #2563eb; }}
    .brief-card-head {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #f1f5f9; padding-bottom: 6px; }}
    .brief-card-head h2 {{ font-size: 16px; margin: 0; font-weight: 700; }}
    .badge {{ background: #eff6ff; color: #1e40af; padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: 800; }}
    .meta-info {{ font-size: 11px; color: #64748b; margin: 6px 0 10px; background: #f8fafc; padding: 4px 8px; border-radius: 6px; display: inline-block; }}
    .step-box {{ margin: 12px 0; border-left: 3px solid #cbd5e1; padding-left: 8px; }}
    .step-box h3 {{ font-size: 12px; margin: 0 0 4px 0; color: #1f2937; font-weight: 700; }}
    .step-box p {{ margin: 0; font-size: 12px; line-height: 1.55; color: #334155; }}
    .inner-summary {{ background: #f8fafc; border: 1px solid #e2e8f0; padding: 8px; border-radius: 8px; font-size: 12px; line-height: 1.5; color: #1e293b; }}
    ul {{ margin: 0; padding-left: 14px; font-size: 12px; color: #475569; line-height: 1.5; }}
    </style>
    </head>
    <body>
    <div class="container">
        <div class="banner">
            <h3 style="margin:0; font-size: 16px;">🧠 제미나이 보유종목 5단계 자산방어 브리핑</h3>
            <p style="margin:4px 0 0 0; font-size:11px; opacity:0.85;">갱신: {now()}</p>
        </div>
        {cards}
    </div>
    </body>
    </html>"""
    Path('docs/details/holding_ai_briefing.html').write_text(page, encoding='utf-8')

if __name__ == '__main__': build()
