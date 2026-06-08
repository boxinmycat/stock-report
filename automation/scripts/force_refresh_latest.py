#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone, timedelta
import csv, html, os
KST=timezone(timedelta(hours=9))
def now(): return datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')
def session():
    env=(os.environ.get('REPORT_SESSION') or os.environ.get('SESSION') or '').strip().upper()
    if env in ('AM','PM','MANUAL'): return env
    h=datetime.now(KST).hour
    return 'AM' if h<12 else 'PM' if h<18 else 'MANUAL'
def read_csv(path,limit=999):
    p=Path(path)
    if not p.exists(): return []
    for enc in ('utf-8-sig','utf-8','cp949','euc-kr'):
        try:
            with p.open(encoding=enc,newline='') as f: return list(csv.DictReader(f))[:limit]
        except Exception: pass
    return []
def esc(x): return html.escape(str(x or ''))
def top15_entry_section():
    rows=read_csv('docs/data/latest_recommendation_top15_full.csv',15)
    if not rows: return "<section class='box accent'><h2>추천 TOP15 + 진입 시나리오</h2><p class='hint'>데이터 확인 필요</p></section>"
    cards=''
    for r in rows[:6]:
        cards += f"""<article class='card'><h3>{esc(r.get('rank'))}. {esc(r.get('stock_name'))} <span>{esc(r.get('score'))}</span></h3><p class='meta'>{esc(r.get('sector'))} · 현재가 {esc(r.get('current_price'))} · {esc(r.get('entry_decision'))}</p><p><b>기본 정보:</b> {esc(r.get('stock_description'))}</p><p><b>공격/기준/보수:</b> {esc(r.get('attack_entry'))} / {esc(r.get('base_entry'))} / {esc(r.get('conservative_entry'))}</p><p><b>손절:</b> {esc(r.get('stop_price'))} · <b>익절:</b> {esc(r.get('take_profit_plan'))}</p></article>"""
    return f"<section class='box accent'><h2>추천 TOP15 + 진입 시나리오</h2><p class='hint'>TOP후보_요약, 진입시나리오, 진입가이드_요약을 합쳐 보여줍니다.</p><div class='grid'>{cards}</div><div class='mini-links'><a href='../details/legacy_top15.html'>TOP15 전체 보기</a><a href='../details/legacy_full_recommendations.html'>전체 추천 명단</a><a href='../details/legacy_continuous.html'>연속추천 관찰</a></div></section>"
def holdings_section():
    rows=read_csv('docs/data/latest_holding_deep_analysis.csv',50); desc={r.get('stock_name'):r for r in read_csv('docs/data/latest_holding_stock_descriptions.csv',50)}
    if not rows: return "<section class='box'><h2>보유종목</h2><p class='hint'>보유종목 데이터 확인 필요</p></section>"
    cards=''
    for r in rows[:8]:
        name=r.get('stock_name'); d=desc.get(name,{})
        cards += f"""<article class='card'><h3>{esc(name)} <span>{esc(r.get('decision'))}</span></h3><p class='meta'>현재가 {esc(r.get('current_price'))} · 손익률 {esc(r.get('unrealized_pnl_pct'))}% · 출처 {esc(r.get('current_price_source'))}</p><p><b>기본 정보:</b> {esc(d.get('stock_description'))}</p></article>"""
    return f"<section class='box'><h2>보유종목 현황</h2><p class='hint'>보유종목 기본 정보와 현재가 판단을 함께 표시합니다. 관련 뉴스는 같은 이름의 다른 회사가 섞이지 않도록 필터를 강화했습니다.</p><div class='grid'>{cards}</div><p class='hint'><a href='../v11_holdings/'>보유종목 상세표 보기</a></p></section>"
def ai_section():
    rows=read_csv('docs/data/latest_holding_ai_briefing.csv',5)
    if not rows: return "<section class='box'><h2>Gemini AI 보유 브리핑</h2><p class='hint'>AI 브리핑은 장마감 리포트에서만 새로 생성합니다.</p></section>"
    cards=''
    for r in rows[:5]:
        summary=r.get('ai_issue_summary') or r.get('ai_three_line_summary') or ''; action=r.get('ai_action_guide') or ''
        cards += f"<article class='card'><h3>{esc(r.get('stock_name'))} <span>{esc(r.get('ai_sentiment'))}</span></h3><p>{esc(summary)}</p><p><b>대응:</b> {esc(action)}</p></article>"
    return f"<section class='box'><h2>Gemini AI 보유 브리핑</h2><p class='hint'>비용 절감을 위해 장마감 리포트에서 주로 갱신합니다.</p>{cards}</section>"
def news_section():
    rows=read_csv('docs/data/latest_news_detail.csv',8); srows=read_csv('docs/data/latest_major_news_summary.csv',1); summary=srows[0].get('summary') if srows else '주요 뉴스 요약 데이터 확인 필요'
    items=''
    for r in rows[:8]:
        if r.get('title'):
            link=r.get('link') or '#'; items += f"<li><a href='{esc(link)}' target='_blank' rel='noopener'>{esc(r.get('title'))}</a><br><span>{esc(r.get('description'))}</span></li>"
    return f"<section class='box'><h2>주요 뉴스 요약</h2><p class='summary'>{esc(summary)}</p><ul>{items}</ul><p class='hint'><a href='../details/naver_news.html'>주요 뉴스 전체 보기</a></p></section>"
def download_section(): return "<section class='box'><h2>엑셀 다운로드</h2><p class='hint'>다운로드 센터 하나로 통합했습니다. 최신 엑셀도 이 안에서 받을 수 있습니다.</p><a class='biglink' href='../downloads/'>다운로드 센터 열기</a></section>"
def optional_strategy_section(): return "<section class='box minor'><h2>검증 참고 자료</h2><p class='hint'>전략 추천/검증은 핵심 화면에서는 작게 두고, 필요할 때만 확인하도록 분리했습니다.</p><a class='biglink' href='../details/legacy_strategy_validation.html'>전략 추천/검증 열기</a></section>"
def unified_html(stamp,ss):
    return f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>주식 리포트 통합 홈</title><style>body{{margin:0;background:#f6f7fb;color:#111827;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}.wrap{{max-width:1120px;margin:auto;padding:20px}}.hero{{background:#111827;color:white;border-radius:22px;padding:22px;margin-bottom:16px}}.hero p{{color:#d1d5db;line-height:1.55}}.nav{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px;margin-bottom:16px}}.nav a,.biglink,.mini-links a{{display:block;background:white;border-radius:16px;padding:14px;text-decoration:none;color:#111827;box-shadow:0 4px 16px #0001;font-weight:700}}.box,.card{{background:white;border-radius:18px;padding:16px;margin-bottom:16px;box-shadow:0 4px 16px #0001}}.accent{{border:1px solid #dbeafe;background:#f8fbff}}.minor{{opacity:.92}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:12px}}.mini-links{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px;margin-top:10px}}h2{{margin:0 0 10px}}h3{{margin:0 0 8px}}p,li,.hint{{font-size:14px;line-height:1.65;color:#374151}}.summary{{background:#eef2ff;border-left:4px solid #2563eb;padding:12px;border-radius:10px}}a{{color:#2563eb;text-decoration:none}}.card span{{font-size:12px;color:#6b7280;font-weight:500}}</style></head><body><main class='wrap'><section class='hero'><h1>주식 리포트 통합 홈</h1><p>갱신: {esc(stamp)} · 세션: {esc(ss)}<br>모바일홈과 최신 리포트를 통합했습니다. 추천 TOP15와 진입 시나리오를 한 화면에서 보고, 보유종목·AI·뉴스·엑셀 다운로드로 이어집니다.</p></section><section class='nav'><a href='../details/legacy_top15.html'>추천 TOP15 + 진입</a><a href='../details/legacy_full_recommendations.html'>전체 추천 명단</a><a href='../details/legacy_continuous.html'>연속추천 관찰</a><a href='../v11_holdings/'>보유종목 상세</a><a href='../details/holding_ai_briefing.html'>AI 보유 브리핑</a><a href='../details/naver_news.html'>주요 뉴스 요약</a><a href='../downloads/'>엑셀 다운로드</a></section>{top15_entry_section()}{holdings_section()}{ai_section()}{news_section()}{download_section()}{optional_strategy_section()}</main><!-- unified-refresh:{esc(stamp)} / {esc(ss)} --></body></html>"""
def main():
    stamp,ss=now(),session(); Path('docs/latest').mkdir(parents=True,exist_ok=True); Path('docs/mobile').mkdir(parents=True,exist_ok=True); Path('docs/data').mkdir(parents=True,exist_ok=True)
    html_text=unified_html(stamp,ss); Path('docs/latest/index.html').write_text(html_text,encoding='utf-8'); Path('docs/mobile/index.html').write_text(html_text,encoding='utf-8')
    Path('docs/data/latest_publish_status.csv').write_text(f'key,value\npublished_at,{stamp}\nsession,{ss}\nsource,unified_legacy_refinement_v12_2_10\n',encoding='utf-8-sig')
    print('✅ unified latest/mobile dashboard rebuilt'); print('✅ TOP15 and entry scenario are integrated'); print('✅ latest publish status csv written')
if __name__=='__main__': main()
