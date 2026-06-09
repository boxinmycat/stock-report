#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone, timedelta
import csv, html, re
KST=timezone(timedelta(hours=9))
def now(): return datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')
def esc(x): return html.escape(str(x or ''))
def read_csv(path,limit=9999):
    p=Path(path)
    if not p.exists(): return []
    for enc in ('utf-8-sig','utf-8','cp949','euc-kr'):
        try:
            with p.open(encoding=enc,newline='') as f: return list(csv.DictReader(f))[:limit]
        except Exception: pass
    return []
def write_csv(rows,path):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    if not rows: rows=[{'message':'데이터 없음','checked_at':now()}]
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
ETF_HINTS={
 '미국 S&P500':'미국 S&P500 지수를 따라가는 상품으로, 애플·마이크로소프트·엔비디아·아마존·알파벳 같은 미국 대형주 흐름을 함께 봅니다.',
 # Example: TIGER 미국배당다우존스
 '미국 배당/다우존스':'미국 배당성장주와 우량 배당주에 분산 투자하는 컨셉으로, 코카콜라·펩시코·홈디포·브로드컴·머크 같은 배당 우량주 흐름을 함께 봅니다.',
 '2차전지':'배터리 셀·소재·장비 등 2차전지 밸류체인 흐름에 투자하는 ETF입니다.',
 '반도체':'메모리·비메모리·장비·소재 등 반도체 밸류체인 흐름을 함께 봅니다.',
 '커버드콜/인컴':'주가 상승 추종보다 월분배와 옵션 프리미엄 인컴 성격이 강한 ETF입니다.',
 '채권/혼합':'금리 변화, 환율, 듀레이션에 민감한 채권 또는 혼합형 ETF입니다.',
 'ETF':'개별 기업이 아니라 특정 지수나 테마를 묶어 추종하는 상장지수펀드입니다.'}
COMPANY_HINTS={
 '대원강업':'자동차용 스프링과 시트 부품 등을 만드는 자동차 부품 기업입니다. 완성차 생산량, 부품 수주, 원가와 환율 흐름이 실적에 영향을 줍니다.',
 '후성':'불소화학과 2차전지 소재, 반도체·디스플레이용 특수가스 흐름과 연결되는 소재 기업입니다. 전방 산업 업황과 원재료 가격, 증설/가동률을 함께 봅니다.',
 '금호타이어':'타이어 제조 기업으로 교체용 타이어와 완성차 공급 흐름을 함께 봅니다. 원재료 가격, 수출, 재무구조 개선 여부가 핵심 체크포인트입니다.',
 '태웅':'대형 단조품을 생산하는 기업으로 풍력, 조선, 플랜트, 산업기계 수요와 연결됩니다. 수주 흐름과 원재료 가격, 전방 투자 사이클을 함께 봅니다.',
 '대한해운':'벌크선 중심의 해운 기업으로 운임지수, 장기운송계약, 유가와 환율 영향을 받습니다.'}
def is_etf(name):
    brands=['KODEX','TIGER','RISE','SOL','ACE','KBSTAR','TIMEFOLIO','HANARO','ARIRANG','PLUS','KoAct','KOSEF']
    up=(name or '').upper(); return any(b.upper() in up for b in brands)
def theme(name):
    n=name or ''
    rules=[('미국 S&P500',['S&P500','S＆P500','미국S&P']),('미국 배당/다우존스',['미국배당','다우존스','SCHD']),('2차전지',['2차전지','배터리']),('반도체',['반도체']),('커버드콜/인컴',['커버드콜','월배당']),('채권/혼합',['미국채','채권','국채','혼합']),('ETF',[])]
    for label,words in rules:
        if any(w in n for w in words): return label
    return 'ETF'
def better_stock_description(name, category):
    return desc(name, category)

def desc(name,category):
    if is_etf(name):
        t=theme(name); return f"{name}은(는) {t} 컨셉의 ETF입니다. {ETF_HINTS.get(t,ETF_HINTS['ETF'])}"
    if name in COMPANY_HINTS: return COMPANY_HINTS[name]
    c=category or ''
    if '자동차' in c: return f"{name}은(는) 자동차 부품·소재 밸류체인과 연결되는 기업입니다. 완성차 생산, 수주, 원가와 환율 흐름을 함께 봅니다."
    if any(x in c for x in ['철강','소재','화학']): return f"{name}은(는) 소재·화학 업황과 연결되는 기업입니다. 원재료 가격, 전방 산업 수요, 수익성 회복 여부가 중요합니다."
    if '반도체' in c: return f"{name}은(는) 반도체 밸류체인과 연결되는 종목입니다. 업황 회복, 장비·소재 투자, 고객사 수요를 함께 봅니다."
    if '바이오' in c: return f"{name}은(는) 바이오·헬스케어 흐름과 연결됩니다. 임상, 허가, 기술이전, 실적 가시성을 함께 확인해야 합니다."
    return f"{name}은(는) {category or '분야 확인 필요'}로 분류된 종목입니다. 사업 내용, 실적 추세, 공시와 수급을 함께 확인해야 합니다."
def pct_values(text, negative_only=False):
    vals=re.findall(r'[-+]?\d+(?:\.\d+)?\s*%', str(text or ''))
    vals=[v.replace(' ','') for v in vals]
    return [v for v in vals if v.startswith('-')] if negative_only else vals
def fmt_tp(text):
    vals=[v for v in pct_values(text) if not v.startswith('-')]
    if len(vals)>=3: return f"<b>{esc(vals[0])}(60)</b> / <b>{esc(vals[1])}(20)</b> / <b>{esc(vals[2])}(20)</b>"
    if len(vals)==2: return f"<b>{esc(vals[0])}(60)</b> / <b>{esc(vals[1])}(40)</b>"
    if len(vals)==1: return f"<b>{esc(vals[0])}</b>"
    return esc(text)
def fmt_sl(text):
    vals=pct_values(text, negative_only=True)
    if vals: return ' / '.join(f"<b>{esc(v)}</b>" for v in vals[:3])
    # fallback for stop price, not percentages
    s=str(text or '').strip()
    return esc(s[:80])
def rebuild_top15():
    rows=read_csv('docs/data/latest_recommendation_top15_full.csv',30)
    if not rows: return
    cards=''
    for r in rows[:15]:
        name=r.get('stock_name') or r.get('종목명'); cat=r.get('sector') or r.get('섹터/분야')
        tp=fmt_tp(r.get('take_profit_plan') or r.get('익절계획') or r.get('take_profit_guide'))
        sl=fmt_sl(r.get('stop_loss_plan') or r.get('손절계획') or r.get('stop_loss_guide') or r.get('stop_price'))
        cards+=f"""<article class='card'><h2>#{esc(r.get('rank'))} {esc(name)}</h2><div class='meta'>{esc(cat)}</div><p>{esc(desc(name,cat))}</p><p><span class='pill'>{esc(r.get('entry_decision') or '조건 확인')}</span></p><p><b>공격/기준/보수:</b> {esc(r.get('attack_entry'))} / {esc(r.get('base_entry'))} / {esc(r.get('conservative_entry'))}</p><p><b>돌파/손절:</b> {esc(r.get('breakout_entry'))} / {esc(r.get('stop_price'))}</p><p><b>익절:</b> {tp}</p><p><b>손절:</b> {sl}</p></article>"""
    css="""body{margin:0;background:#f6f7fb;color:#111827;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}.wrap{max-width:980px;margin:auto;padding:20px}.hero{background:#172554;color:white;border-radius:22px;padding:22px;margin-bottom:16px}.hero p{color:#dbeafe;line-height:1.55}.card{background:white;border-radius:20px;padding:18px;margin-bottom:16px;box-shadow:0 4px 16px #0001}.card h2{font-size:22px;margin:0 0 10px}.meta{font-size:14px;color:#6b7280;margin-bottom:12px}.pill{display:inline-block;background:#dbeafe;color:#1e40af;border-radius:999px;padding:8px 12px;font-weight:700}p{font-size:15px;line-height:1.7;color:#374151}b{color:#111827}"""
    html_text=f"<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>추천 TOP15 + 진입 시나리오</title><style>{css}</style></head><body><main class='wrap'><section class='hero'><h1>추천 TOP15 + 진입 시나리오</h1><p>추천 후보를 처음 보는 사람도 어떤 기업/ETF인지 먼저 이해할 수 있도록 기본 정보를 정리했습니다.</p></section>{cards}</main></body></html>"
    Path('docs/details/legacy_top15.html').write_text(html_text,encoding='utf-8'); Path('docs/details/recommendation_top15.html').write_text(html_text,encoding='utf-8')
def restyle(path):
    p=Path(path)
    if not p.exists(): return
    txt=p.read_text(encoding='utf-8')
    txt=txt.replace('min-width:900px','min-width:1250px').replace('width:100%;','width:max-content;min-width:100%;')
    txt=txt.replace('</style>', "td:nth-child(n+8){min-width:380px;max-width:560px;}td:nth-child(-n+7){min-width:95px;max-width:180px;}td{word-break:keep-all;white-space:normal;}</style>")
    p.write_text(txt,encoding='utf-8')
def news_page():
    rows=read_csv('docs/data/latest_news_detail.csv',100)
    recent=[r for r in rows if 'May' not in (r.get('pubDate') or '') and ' 5월 ' not in (r.get('title') or '')]
    use=(recent or rows)[:20]
    summary=read_csv('docs/data/latest_major_news_summary.csv',1); s=summary[0].get('summary') if summary else '최신 뉴스 요약 데이터 확인 필요'
    items=''
    for r in use:
        link=r.get('link') or '#'; items+=f"<article class='card'><div class='meta'>{esc(r.get('query'))} · {esc(r.get('pubDate'))}</div><h2>{esc(r.get('title'))}</h2><p>{esc(r.get('description'))}</p><a href='{esc(link)}' target='_blank' rel='noopener'>기사 보기</a></article>"
    css="""body{margin:0;background:#f6f7fb;color:#111827;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}.wrap{max-width:900px;margin:auto;padding:20px}.hero{background:#064e3b;color:white;border-radius:22px;padding:22px;margin-bottom:16px}.hero p{color:#d1fae5;line-height:1.55}.summary{background:#ecfdf5;border-left:4px solid #059669;padding:14px;border-radius:12px;line-height:1.65}.card{background:white;border-radius:18px;padding:16px;margin-bottom:12px;box-shadow:0 4px 16px #0001}.card h2{font-size:17px;margin:6px 0}.meta{font-size:12px;color:#059669}p{font-size:14px;line-height:1.6;color:#374151}a{color:#2563eb;font-weight:700;text-decoration:none}"""
    Path('docs/details/naver_news.html').write_text(f"<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>주요 뉴스 요약</title><style>{css}</style></head><body><main class='wrap'><section class='hero'><h1>주요 뉴스 요약</h1><p>오래된 기사 fallback을 줄이고, 최근 기사 중심으로 정리합니다.</p></section><section class='summary'>{esc(s)}</section>{items}</main></body></html>",encoding='utf-8')
def main():
    rebuild_top15(); restyle('docs/details/legacy_full_recommendations.html'); restyle('docs/details/recommendation_full_list.html'); restyle('docs/details/legacy_candidate_dashboard_validation.html'); news_page()
    print('✅ v12.2.13 UI and info refinements applied')
if __name__=='__main__': main()
