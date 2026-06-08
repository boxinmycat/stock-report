#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone, timedelta
import html, json, os, re, time, urllib.request
import pandas as pd

KST = timezone(timedelta(hours=9))

def now():
    return datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')

def read_csv(path):
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()
    for enc in ('utf-8-sig', 'utf-8', 'cp949', 'euc-kr'):
        try:
            return pd.read_csv(p, dtype=str, encoding=enc).fillna('')
        except Exception:
            pass
    return pd.DataFrame()

def write_csv(df, path):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.fillna('').to_csv(p, index=False, encoding='utf-8-sig')

def s(x):
    if x is None:
        return ''
    v = str(x).strip()
    return '' if v.lower() in ('nan', 'none', 'null') else v

def pick(row, *names):
    for n in names:
        if n in row and s(row.get(n)):
            return s(row.get(n))
    lower = {str(k).lower(): k for k in row.keys()}
    for n in names:
        k = lower.get(n.lower())
        if k and s(row.get(k)):
            return s(row.get(k))
    return ''

def related_news(news, name, limit=5):
    if news.empty or not name:
        return []
    rows = []
    tokens = [t for t in re.split(r'[\s/·,_-]+', name) if len(t) >= 3]
    for _, r in news.iterrows():
        txt = ' '.join([pick(r, 'query'), pick(r, 'title'), pick(r, 'description')])
        score = 0
        if pick(r, 'query') == name:
            score += 10
        if name in txt:
            score += 6
        score += sum(1 for t in tokens if t in txt)
        if score > 0:
            rows.append((score, {
                'title': pick(r, 'title') or '제목 없음',
                'description': pick(r, 'description'),
                'link': pick(r, 'link'),
                'pubDate': pick(r, 'pubDate'),
            }))
    rows.sort(key=lambda x: x[0], reverse=True)
    return [x[1] for x in rows[:limit]]

def fallback(row, links, reason='fallback_rule'):
    name = pick(row, 'stock_name')
    decision = pick(row, 'decision')
    pnl = pick(row, 'unrealized_pnl_pct')
    price_source = pick(row, 'current_price_source')
    titles = ' / '.join(x['title'] for x in links[:2]) if links else '연결 뉴스 부족'
    issue = f'{name} 관련 뉴스 {len(links)}건을 기준으로 점검했습니다. Gemini 호출이 실패했거나 응답을 파싱하지 못해 규칙 기반으로 표시합니다. 주요 기사 흐름은 {titles} 입니다.'
    return {
        'ai_status': reason,
        'ai_model': 'fallback',
        'ai_summary': issue,
        'issue_overview': issue,
        'positive_view': '긍정/리스크 판단은 Gemini 응답 실패로 제한적입니다. 뉴스 링크와 가격 흐름을 직접 확인하세요.',
        'risk_view': '현재가 출처와 종목코드를 먼저 확인하고, 손절가 아래에서 추가매수하지 않는 기준을 유지하세요.',
        'action_comment': f'현재 판단은 {decision or "HOLD"}입니다. 손익률 {pnl or "계산 대기"}%, 가격출처 {price_source or "확인 필요"} 기준으로 분할 대응하세요.',
        'confidence': '낮음',
    }

def make_prompt(row, links):
    news_text = '\n'.join([f"- 제목: {x['title']}\n  요약: {x['description']}\n  링크: {x['link']}" for x in links]) or '관련 뉴스 부족'
    return f'''너는 한국 주식 보유종목 점검용 리포트 보조 분석가다. 매수/매도 확정 지시가 아니라 보유자 관점의 판단 보조를 작성한다.
반드시 JSON만 출력하라. 필드: ai_summary, issue_overview, positive_view, risk_view, action_comment, confidence.
각 필드는 한국어 2~4문장으로 자세히 작성한다. 과장하지 말고 근거가 약하면 약하다고 말한다.

[보유종목]
종목명: {pick(row, 'stock_name')}
종목코드: {pick(row, 'stock_code')}
현재가: {pick(row, 'current_price')}
평균단가: {pick(row, 'avg_price')}
손익률: {pick(row, 'unrealized_pnl_pct')}
현재 판단: {pick(row, 'decision')}
가격 출처: {pick(row, 'current_price_source')}

[관련 뉴스]
{news_text}
'''

def extract_json(text):
    text = text.strip()
    if text.startswith('```'):
        text = re.sub(r'^```(?:json)?', '', text).strip()
        text = re.sub(r'```$', '', text).strip()
    m = re.search(r'\{.*\}', text, re.S)
    if m:
        text = m.group(0)
    return json.loads(text)

def call_gemini(prompt):
    key = os.environ.get('GEMINI_API_KEY', '').strip()
    primary = os.environ.get('GEMINI_MODEL', 'gemini-3.5-flash').strip() or 'gemini-3.5-flash'
    models = [primary]
    for model in ('gemini-2.5-flash', 'gemini-2.5-flash-lite'):
        if model not in models:
            models.append(model)
    if not key:
        raise RuntimeError('GEMINI_API_KEY missing')

    body = json.dumps({
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {'temperature': 0.25, 'maxOutputTokens': 1200, 'responseMimeType': 'application/json'},
    }).encode('utf-8')

    last_error = None
    for model in models:
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
        req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json', 'x-goog-api-key': key})
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                data = json.loads(res.read().decode('utf-8'))
            text = data['candidates'][0]['content']['parts'][0].get('text', '').strip()
            out = extract_json(text)
            out['ai_model'] = model
            return out
        except Exception as e:
            last_error = e
            continue
    raise RuntimeError(f'Gemini all models failed: {last_error!r}')

def build():
    holdings = read_csv('docs/data/latest_holding_deep_analysis.csv')
    news = read_csv('docs/data/latest_news_detail.csv')
    rows = []
    cards = ''

    if holdings.empty:
        write_csv(pd.DataFrame([{'ai_status': 'no_holdings', 'message': '보유종목 데이터 없음', 'checked_at': now()}]), 'docs/data/latest_holding_ai_briefing.csv')
        return

    for _, h in holdings.iterrows():
        links = related_news(news, pick(h, 'stock_name'))
        try:
            out = call_gemini(make_prompt(h, links))
            out['ai_status'] = 'gemini_ok'
        except Exception as e:
            out = fallback(h, links, 'fallback_rule')
            out['error'] = repr(e)

        row = {
            'stock_name': pick(h, 'stock_name'),
            'stock_code': pick(h, 'stock_code'),
            'decision': pick(h, 'decision'),
            'current_price': pick(h, 'current_price'),
            'avg_price': pick(h, 'avg_price'),
            'pnl_pct': pick(h, 'unrealized_pnl_pct'),
            'price_source': pick(h, 'current_price_source'),
            'checked_at': now(),
            **out,
        }
        for i, x in enumerate(links[:5], 1):
            row[f'news_title_{i}'] = x['title']
            row[f'news_link_{i}'] = x['link']
            row[f'news_desc_{i}'] = x['description']
        rows.append(row)

        news_html = ''.join(
            f"<li><b>{html.escape(x['title'])}</b><br><span>{html.escape(x['description'][:180])}</span><br><a href='{html.escape(x['link'])}' target='_blank' rel='noopener'>기사 보기</a></li>"
            for x in links if x.get('link')
        ) or '<li>연결 뉴스 부족</li>'
        cards += f"""<article class='card'><div class='head'><h2>{html.escape(row['stock_name'])}</h2><span>{html.escape(row['ai_status'])} · {html.escape(row.get('ai_model',''))}</span></div><div class='meta'>현재가 {html.escape(row['current_price'])} · 평균단가 {html.escape(row['avg_price'])} · 손익률 {html.escape(row['pnl_pct'])}% · 판단 {html.escape(row['decision'])}</div><section><h3>AI 요약</h3><p>{html.escape(row.get('ai_summary',''))}</p></section><section><h3>현재 이슈</h3><p>{html.escape(row.get('issue_overview',''))}</p></section><section><h3>긍정 포인트</h3><p>{html.escape(row.get('positive_view',''))}</p></section><section><h3>리스크 포인트</h3><p>{html.escape(row.get('risk_view',''))}</p></section><section><h3>대응 가이드</h3><p>{html.escape(row.get('action_comment',''))}</p></section><section><h3>관련 뉴스</h3><ul>{news_html}</ul></section></article>"""
        time.sleep(0.1)

    write_csv(pd.DataFrame(rows), 'docs/data/latest_holding_ai_briefing.csv')
    Path('docs/details').mkdir(parents=True, exist_ok=True)
    Path('docs/details/holding_ai_briefing.html').write_text(f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Gemini AI 보유종목 브리핑</title><style>body{{margin:0;background:#f6f7fb;color:#111827;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}.wrap{{max-width:980px;margin:auto;padding:20px}}.hero{{background:#1f2937;color:white;border-radius:22px;padding:22px;margin-bottom:16px}}.hero p{{color:#d1d5db;line-height:1.55}}.card{{background:white;border-radius:20px;padding:18px;margin-bottom:16px;box-shadow:0 4px 16px #0001}}.head{{display:flex;justify-content:space-between;gap:12px;align-items:center;border-bottom:1px solid #e5e7eb;padding-bottom:10px;margin-bottom:12px}}.head h2{{margin:0;font-size:21px}}.head span{{background:#eef2ff;color:#3730a3;border-radius:999px;padding:6px 10px;font-weight:700;font-size:12px}}.meta{{font-size:13px;color:#6b7280;margin-bottom:14px;line-height:1.5}}section{{margin:14px 0}}h3{{font-size:15px;margin:0 0 6px}}p,li{{font-size:14px;line-height:1.72;color:#374151}}a{{color:#2563eb;font-weight:700;text-decoration:none}}</style></head><body><main class='wrap'><section class='hero'><h1>Gemini AI 보유종목 브리핑</h1><p>갱신: {html.escape(now())}<br>보유종목 현재가와 네이버뉴스를 Gemini가 해석한 브리핑입니다. 매수·매도 확정 지시가 아니라 판단 보조 자료입니다.</p></section>{cards}</main></body></html>""", encoding='utf-8')
    print('✅ Gemini holding AI briefing built')
    print(f'rows: {len(rows)}')

if __name__ == '__main__':
    build()
