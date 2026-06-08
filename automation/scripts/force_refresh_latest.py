#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone, timedelta
import csv, html, os

KST = timezone(timedelta(hours=9))

def now():
    return datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')

def session():
    env = (os.environ.get('REPORT_SESSION') or os.environ.get('SESSION') or '').strip().upper()
    if env in ('AM', 'PM', 'MANUAL'):
        return env
    hour = datetime.now(KST).hour
    return 'AM' if hour < 12 else 'PM' if hour < 18 else 'MANUAL'

def read_csv(path, limit=999):
    p = Path(path)
    if not p.exists():
        return []
    for enc in ('utf-8-sig', 'utf-8', 'cp949', 'euc-kr'):
        try:
            with p.open(encoding=enc, newline='') as f:
                return list(csv.DictReader(f))[:limit]
        except Exception:
            pass
    return []

def esc(x):
    return html.escape(str(x or ''))

def latest_html(stamp, ss):
    holdings = read_csv('docs/data/latest_holding_deep_analysis.csv')
    ai = read_csv('docs/data/latest_holding_ai_briefing.csv')
    news = read_csv('docs/data/latest_news_detail.csv', 8)

    hold_rows = ''.join(
        f"<tr><td>{esc(r.get('stock_name'))}</td><td>{esc(r.get('stock_code'))}</td><td>{esc(r.get('decision'))}</td>"
        f"<td>{esc(r.get('avg_price'))}</td><td>{esc(r.get('current_price'))}</td><td>{esc(r.get('unrealized_pnl_pct'))}</td>"
        f"<td>{esc(r.get('current_price_source'))}</td></tr>"
        for r in holdings
    ) or '<tr><td colspan="7">보유종목 데이터 확인 필요</td></tr>'

    ai_cards = ''
    for r in ai[:5]:
        ai_cards += (
            f"<article class='card'><h3>{esc(r.get('stock_name'))} <span>{esc(r.get('ai_status'))}</span></h3>"
            f"<p>{esc(r.get('ai_summary') or r.get('issue_overview'))}</p>"
            f"<p><b>대응:</b> {esc(r.get('action_comment'))}</p></article>"
        )
    if not ai_cards:
        ai_cards = '<article class="card"><h3>Gemini AI 브리핑</h3><p>데이터 확인 필요</p></article>'

    news_list = ''.join(
        f"<li><a href='{esc(r.get('link'))}' target='_blank' rel='noopener'>{esc(r.get('title'))}</a><br>"
        f"<span>{esc(r.get('description'))}</span></li>"
        for r in news if r.get('title')
    ) or '<li>뉴스 데이터 확인 필요</li>'

    return f"""<!doctype html>
<html lang='ko'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Stock Report Latest</title>
<style>
body{{margin:0;background:#f6f7fb;color:#111827;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}
.wrap{{max-width:1080px;margin:auto;padding:20px}}
.hero{{background:#111827;color:white;border-radius:22px;padding:22px;margin-bottom:16px}}
.hero p{{color:#d1d5db}}
.links{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px;margin-bottom:16px}}
.link{{background:white;border-radius:16px;padding:14px;text-decoration:none;color:#111827;box-shadow:0 4px 16px #0001;font-weight:700}}
.box,.card{{background:white;border-radius:18px;padding:16px;margin-bottom:16px;box-shadow:0 4px 16px #0001}}
.tablewrap{{overflow:auto}}
table{{border-collapse:collapse;width:100%;min-width:840px}}
th,td{{border-bottom:1px solid #e5e7eb;padding:9px;font-size:13px;text-align:left}}
th{{background:#f3f4f6}}
h2{{margin:0 0 10px}} h3{{margin:0 0 8px}}
p,li{{font-size:14px;line-height:1.65;color:#374151}}
a{{color:#2563eb;text-decoration:none}}
</style>
</head>
<body>
<main class='wrap'>
<section class='hero'>
<h1>최신 주식 리포트</h1>
<p>갱신: {esc(stamp)} · 세션: {esc(ss)}<br>이 페이지는 기존 리포트 HTML을 그대로 복사하지 않고, 최신 CSV 데이터를 기준으로 다시 구성합니다.</p>
</section>
<section class='links'>
<a class='link' href='../v11_holdings/'>보유종목 상세</a>
<a class='link' href='../details/holding_ai_briefing.html'>Gemini AI 브리핑</a>
<a class='link' href='../details/naver_news.html'>네이버뉴스 상세</a>
<a class='link' href='../strategy/'>전략검증</a>
</section>
<section class='box'>
<h2>보유종목 현재가 현황</h2>
<div class='tablewrap'><table><thead><tr><th>종목</th><th>코드</th><th>판단</th><th>평균단가</th><th>현재가</th><th>손익률%</th><th>출처</th></tr></thead><tbody>{hold_rows}</tbody></table></div>
</section>
<section><h2>Gemini AI 보유 브리핑</h2>{ai_cards}</section>
<section class='box'><h2>네이버뉴스 상세 일부</h2><ul>{news_list}</ul></section>
</main>
<!-- latest-refresh: {esc(stamp)} / {esc(ss)} -->
</body>
</html>"""

def main():
    stamp, ss = now(), session()
    Path('docs/latest').mkdir(parents=True, exist_ok=True)
    Path('docs/mobile').mkdir(parents=True, exist_ok=True)
    Path('docs/data').mkdir(parents=True, exist_ok=True)

    Path('docs/latest/index.html').write_text(latest_html(stamp, ss), encoding='utf-8')

    links = [
        ('최신 리포트', '../latest/'),
        ('보유종목', '../v11_holdings/'),
        ('Gemini AI 브리핑', '../details/holding_ai_briefing.html'),
        ('네이버뉴스', '../details/naver_news.html'),
        ('전략검증', '../strategy/'),
    ]
    cards = ''.join(f"<a class='card' href='{u}'><b>{t}</b><span>열기</span></a>" for t, u in links)
    Path('docs/mobile/index.html').write_text(f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><style>body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f6f7fb;margin:0}}.wrap{{max-width:860px;margin:auto;padding:20px}}.hero{{background:#111827;color:white;border-radius:22px;padding:22px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin-top:14px}}.card{{display:flex;justify-content:space-between;text-decoration:none;color:#111827;background:white;border-radius:18px;padding:18px;box-shadow:0 4px 16px #0001}}</style></head><body><main class='wrap'><section class='hero'><h1>주식 리포트 모바일 홈</h1><p>최근 갱신: {stamp}<br>세션: {ss}</p></section><section class='grid'>{cards}</section></main></body></html>""", encoding='utf-8')
    Path('docs/data/latest_publish_status.csv').write_text(f'key,value\npublished_at,{stamp}\nsession,{ss}\nsource,clean_latest_dashboard\n', encoding='utf-8-sig')
    print('✅ clean latest dashboard rebuilt from current CSV data')
    print('✅ latest publish status csv written')

if __name__ == '__main__':
    main()
