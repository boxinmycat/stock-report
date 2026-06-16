#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone, timedelta
import csv, html, os, re

KST = timezone(timedelta(hours=9))
def now(): return datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')
def session():
    env = (os.environ.get('REPORT_SESSION') or os.environ.get('SESSION') or '').strip().upper()
    if env in ('AM','PM','PM_TEST','MANUAL'): return env
    h = datetime.now(KST).hour
    return 'AM' if h < 12 else 'PM' if h < 18 else 'MANUAL'

def read_csv(path, limit=999):
    p = Path(path)
    if not p.exists(): return []
    for enc in ('utf-8-sig','utf-8','cp949','euc-kr'):
        try:
            with p.open(encoding=enc,newline='') as f: return list(csv.DictReader(f))[:limit]
        except Exception: pass
    return []

def esc(x): return html.escape(str(x or ''))

def _pct_values(text):
    # [손절 버그 소거] 정규식 매칭을 최대 3개로 잘라 분할 비중(80%) 수치가 달라붙는 버그를 종결
    vals = [v.replace(' ', '') for v in re.findall(r"[\+\-]?\d+(?:\.\d+)?\s*%", str(text or ''))]
    return vals[:3]

def fmt_tp(text):
    vals = _pct_values(text)
    if len(vals) >= 3: return f"<b>{esc(vals[0])}(60)</b> / <b>{esc(vals[1])}(20)</b> / <b>{esc(vals[2])}(20)</b>"
    if len(vals) == 2: return f"<b>{esc(vals[0])}(60)</b> / <b>{esc(vals[1])}(40)</b>"
    if vals: return f"<b>{esc(vals[0])}</b>"
    return esc(text)

def fmt_sl(text):
    vals = _pct_values(text)
    if vals: return ' / '.join(f"<span style='color:#dc2626; font-weight:bold;'>{esc(v)}</span>" for v in vals)
    return esc(text)

def top15_entry_section():
    rows = read_csv('docs/data/latest_recommendation_top15_full.csv', 15)
    if not rows: return "<section class='box accent'><h2>추천 TOP15 + 진입 시나리오</h2><p class='hint'>데이터 확인 필요</p></section>"
    cards = ''
    for r in rows[:6]:
        cards += f"""
        <article class='card'>
            <h3>{esc(r.get('rank'))}. {esc(r.get('stock_name'))} <span class='pill'>{esc(r.get('score'))}점</span></h3>
            <p class='meta'>{esc(r.get('sector'))} · 현재가 {esc(r.get('current_price'))} · {esc(r.get('entry_decision'))}</p>
            <p class='desc'>💡 <b>리서치:</b> {esc(r.get('stock_description'))}</p>
            <p style="font-size:12px; margin:2px 0;">🎯 <b>익절계획:</b> {fmt_tp(r.get('take_profit_plan'))}</p>
            <p style="font-size:12px; margin:2px 0;">🚨 <b>손절계획:</b> {fmt_sl(r.get('stop_loss_plan') or r.get('stop_price'))}</p>
        </article>"""
    return f"<section class='box accent'><h2>💎 추천 후보 TOP6 요약</h2><div class='vertical-grid'>{cards}</div></section>"

def holdings_section():
    rows = read_csv('docs/data/latest_holding_deep_analysis.csv', 50)
    desc = {r.get('stock_name'): r for r in read_csv('docs/data/latest_holding_stock_descriptions.csv', 50)}
    if not rows: return "<section class='box'><h2>보유종목 현황</h2><p class='hint'>보유 종목 내역이 없습니다.</p></section>"
    cards = ''
    for r in rows[:8]:
        name = r.get('stock_name')
        d = desc.get(name, {})
        pnl = float(r.get('unrealized_pnl_pct', 0) or 0)
        pnl_cls = "profit" if pnl > 0 else "loss" if pnl < 0 else "neutral"
        cards += f"""
        <article class='card' style='border-left:5px solid #2563eb;'>
            <h3>{esc(name)} <span class='pill' style='background:#eff6ff; color:#1e40af;'>{esc(r.get('decision'))}</span></h3>
            <p class='meta'>현재가 {esc(r.get('current_price'))} · 손익률 <b class='{pnl_cls}'>{esc(r.get('unrealized_pnl_pct'))}%</b></p>
        </article>"""
    return f"<section class='box'><h2>📊 실시간 보유종목 상태</h2><div class='vertical-grid'>{cards}</div></section>"

def ai_section():
    rows = read_csv('docs/data/latest_holding_ai_briefing.csv', 5)
    if not rows: return "<section class='box'><h2>🧠 제미나이 AI 보유 브리핑</h2><p class='hint'>장마감 리포트에서 분석이 반영됩니다.</p></section>"
    cards = ''
    for r in rows[:5]:
        summary_raw = r.get('ai_issue_summary') or r.get('ai_three_line_summary') or ''
        summary_text = str(summary_raw).replace('\n', '<br>')
        action = r.get('ai_action_headline') or r.get('ai_action_guide') or ''
        cards += f"""
        <article class='card' style='border-top:3px solid #1e3a8a;'>
            <h3>{esc(r.get('stock_name'))} <span class='pill' style='background:#f0fdf4; color:#166534;'>{esc(action)}</span></h3>
            <p class='desc' style='font-size:12px;'>{summary_text}</p>
        </article>"""
    return f"<section class='box'><h2>🧠 제미나이 자산방어 브리핑</h2>{cards}</section>"

def news_section():
    rows = read_csv('docs/data/latest_news_detail.csv', 6)
    items = ''
    for r in rows:
        if r.get('title'):
            link = r.get('link') or '#'
            items += f"""
            <article class='card'>
                <small style='color:#059669; font-weight:700;'>{esc(r.get('publisher'))} · {esc(r.get('query'))}</small>
                <h4 style='margin:4px 0 2px 0; font-size:14px;'><a href='{esc(link)}' target='_blank' style='color:#111827;'>{esc(r.get('title'))}</a></h4>
            </article>"""
    return f"<section class='box'><h2>📰 당일 주요 뉴스</h2><div class='vertical-grid'>{items}</div></section>"

def download_section(): return "<section class='box'><h2>엑셀 다운로드</h2><p class='hint'>최신 분석 엑셀 리포트 다운로드 보관소</p><a class='biglink' href='../downloads/' style='display:block; background:white; border-radius:16px; padding:14px; text-decoration:none; color:#111827; box-shadow:0 4px 16px rgba(0,0,0,0.05); font-weight:700;'>다운로드 센터 열기</a></section>"

def unified_html(stamp, ss):
    return f"""<!doctype html>
<html lang='ko'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>모바일 통합 관제 홈</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,"Malgun Gothic",sans-serif;background:#f3f4f6;margin:0;padding:12px;color:#111827}}
.wrap{{max-width:480px;margin:0 auto;}}
.hero{{background:linear-gradient(135deg,#111827,#1f2937);color:white;border-radius:16px;padding:16px;margin-bottom:12px}}
.hero h1{{margin:0;font-size:18px;font-weight:800}}
.hero p{{margin:4px 0 0;font-size:11px;opacity:0.8}}
.nav-grid{{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:12px}}
.nav-grid a{{display:block;background:white;border-radius:10px;padding:10px;text-align:center;font-size:12px;font-weight:700;color:#1e3a8a;text-decoration:none;box-shadow:0 2px 4px rgba(0,0,0,0.02);border:1px solid #e5e7eb}}
.box{{margin-bottom:14px}}
.box h2{{font-size:14px;margin:0 0 8px 0;border-left:4px solid #1e3a8a;padding-left:6px;font-weight:800}}
.vertical-grid{{display:flex;flex-direction:column;gap:8px}}
.card{{background:white;border-radius:12px;padding:12px;box-shadow:0 2px 4px rgba(0,0,0,0.02);border:1px solid #e5e7eb}}
.card h3{{margin:0 0 4px 0;font-size:14px;font-weight:700;display:flex;justify-content:space-between;align-items:center}}
.pill{{font-size:10px;background:#eef2ff;color:#3730a3;padding:2px 6px;border-radius:4px}}
.meta{{font-size:11px;color:#6b7280;margin:2px 0}}
.desc{{background:#f9fafb;padding:8px;border-radius:6px;font-size:12px;color:#374151;margin:4px 0;line-height:1.4}}
.profit{{color:#dc2626}}.loss{{color:#2563eb}}.neutral{{color:#4b5563}}
</style>
</head>
<body>
<main class='wrap'>
    <section class='hero'>
        <h1>📱 모바일 관제 대시보드</h1>
        <p>갱신: {esc(stamp)} | 세션: {esc(ss)}</p>
    </section>
    <section class='nav-grid'>
        <a href='../details/legacy_top15.html'>TOP15 리서치</a>
        <a href='../details/legacy_continuous.html'>🔄 연속추천 관찰</a>
        <a href='../v11_holdings/'>보유종목 상세</a>
        <a href='../details/holding_ai_briefing.html'>🧠 AI 자산 브리핑</a>
        <a href='../details/naver_news.html'>📰 뉴스 3줄요약</a>
        <a href='../downloads/' style='grid-column: span 2; background:#1e3a8a; color:white;'>📥 전체 엑셀 센터 열기</a>
    </section>
    {top15_entry_section()}
    {holdings_section()}
    {ai_section()}
    {news_section()}
    {download_section()}
</main>
</body>
</html>"""

def main():
    stamp, ss = now(), session()
    Path('docs/latest').mkdir(parents=True, exist_ok=True)
    Path('docs/mobile').mkdir(parents=True, exist_ok=True)
    
    html_text = unified_html(stamp, ss)
    Path('docs/mobile/index.html').write_text(html_text, encoding='utf-8')
    Path('docs/latest/index.html').write_text("<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta http-equiv='refresh' content='0; url=../mobile/'><meta name='viewport' content='width=device-width,initial-scale=1'></head><body></body></html>", encoding='utf-8')
    print('✅ 에러 없는 모바일 전용 480px 강력 압축 홈 대시보드 및 포맷 버그 완전 가동.')

if __name__ == '__main__': main()
