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

def pick(row, names):
    if not row:
        return ''
    lower = {str(k).strip().lower(): k for k in row.keys()}
    for name in names:
        k = lower.get(name.lower())
        if k and str(row.get(k, '')).strip():
            return str(row.get(k, '')).strip()
    for k, v in row.items():
        kk = str(k).strip().lower()
        for name in names:
            if name.lower() in kk and str(v).strip():
                return str(v).strip()
    return ''

def first_existing_csv(paths, limit=999):
    for p in paths:
        rows = read_csv(p, limit)
        if rows:
            return p, rows
    return '', []

def candidate_data():
    paths = [
        'docs/data/latest_candidates.csv',
        'docs/data/latest_candidate_detail.csv',
        'docs/data/latest_recommendations.csv',
        'docs/data/latest_recommendation_tracking.csv',
        'docs/data/latest_strategy_validation_detail.csv',
        'recommendation_tracking.csv',
    ]
    source, rows = first_existing_csv(paths, 30)
    filtered = []
    for r in rows:
        name = pick(r, ['stock_name', '종목명', 'name', 'candidate_name'])
        if name:
            filtered.append(r)
    return source, filtered[:12]

def strategy_data():
    source, rows = first_existing_csv([
        'docs/data/latest_strategy_validation_summary.csv',
        'docs/data/latest_strategy_test.csv',
        'docs/data/latest_tpsl_strategy_guide.csv',
    ], 12)
    return source, rows


def download_section():
    downloads = read_csv('docs/data/latest_downloads.csv', 10)
    if not downloads:
        return """<section class='box'><h2>엑셀/상세파일 다운로드</h2><p class='hint'>아직 다운로드 파일이 생성되지 않았습니다. workflow의 Publish Excel download files 단계를 확인하세요.</p></section>"""
    cards = ''
    for r in downloads[:6]:
        label = pick(r, ['label', '파일명'])
        url = pick(r, ['url'])
        size = pick(r, ['size_kb'])
        source = pick(r, ['source'])
        href = '../downloads/' + url.replace('./', '') if url else '../downloads/'
        cards += f"<a class='download' href='{esc(href)}' download><b>{esc(label)}</b><span>{esc(size)} KB</span><small>{esc(source)}</small></a>"
    return f"<section class='box download-box'><h2>엑셀/상세파일 다운로드</h2><p class='hint'>세밀하게 보고 싶을 때는 최신 엑셀 리포트를 내려받아 확인하세요. 모바일에서는 다운로드 후 Excel·Numbers·Google Sheets 앱으로 열면 됩니다.</p><div class='downloads'>{cards}</div><p class='hint'><a href='../downloads/'>다운로드 센터 전체 보기</a></p></section>"


def recommendation_section():
    source, rows = candidate_data()
    if rows:
        trs = ''
        for r in rows[:10]:
            name = pick(r, ['stock_name', '종목명', 'name', 'candidate_name'])
            code = pick(r, ['stock_code', '종목코드', 'code', 'ticker'])
            score = pick(r, ['score', '점수', '추천점수', 'rank_score', 'total_score'])
            sector = pick(r, ['sector', '분야', 'theme', '테마', 'industry'])
            reason = pick(r, ['reason', '추천사유', 'comment', 'memo', 'signal', '판단', 'decision'])
            price = pick(r, ['current_price', '현재가', 'price', '기준가', '추천가', 'close'])
            trs += f"<tr><td>{esc(name)}</td><td>{esc(code)}</td><td>{esc(score)}</td><td>{esc(price)}</td><td>{esc(sector)}</td><td>{esc(reason)}</td></tr>"
        body = f"""
        <p class='hint'>데이터 출처: {esc(source)} · 추천 후보는 매수 확정이 아니라 관찰 후보입니다.</p>
        <div class='tablewrap'><table>
        <thead><tr><th>종목</th><th>코드</th><th>점수</th><th>기준가/현재가</th><th>분야</th><th>근거/판단</th></tr></thead>
        <tbody>{trs}</tbody></table></div>
        """
    else:
        body = """
        <p class='hint'>추천후보 CSV가 없거나 컬럼명이 달라 표를 만들지 못했습니다. 대신 기존 추천종목 상세 페이지 링크를 유지합니다.</p>
        <div class='mini-links'>
          <a href='../details/candidate_detail.html'>추천후보 상세 보기</a>
          <a href='../details/continuous.html'>연속추천/관찰 보기</a>
          <a href='../strategy/'>전략검증 보기</a>
        </div>
        """
    return f"<section class='box accent'><h2>추천 종목·관심 후보</h2>{body}</section>"

def strategy_section():
    source, rows = strategy_data()
    if not rows:
        return """<section class='box'><h2>추천전략 검증</h2><p class='hint'>전략검증 데이터 확인 필요. <a href='../strategy/'>전략검증 페이지 열기</a></p></section>"""
    trs = ''
    for r in rows[:8]:
        strategy = pick(r, ['strategy', '전략', 'model', 'case'])
        verdict = pick(r, ['verdict', '판정', 'status', '결과'])
        avg = pick(r, ['avg_return', '평균수익률', 'return', '수익률'])
        win = pick(r, ['win_rate', '승률'])
        memo = pick(r, ['memo', 'comment', 'guide', '설명'])
        trs += f"<tr><td>{esc(strategy)}</td><td>{esc(verdict)}</td><td>{esc(avg)}</td><td>{esc(win)}</td><td>{esc(memo)}</td></tr>"
    return f"""
    <section class='box'>
      <h2>추천전략 검증</h2>
      <p class='hint'>데이터 출처: {esc(source)}</p>
      <div class='tablewrap'><table><thead><tr><th>전략</th><th>판정</th><th>평균수익률</th><th>승률</th><th>메모</th></tr></thead><tbody>{trs}</tbody></table></div>
    </section>
    """

def holdings_section():
    holdings = read_csv('docs/data/latest_holding_deep_analysis.csv')
    rows = ''.join(
        f"<tr><td>{esc(r.get('stock_name'))}</td><td>{esc(r.get('stock_code'))}</td><td>{esc(r.get('decision'))}</td>"
        f"<td>{esc(r.get('avg_price'))}</td><td>{esc(r.get('current_price'))}</td><td>{esc(r.get('unrealized_pnl_pct'))}</td>"
        f"<td>{esc(r.get('current_price_source'))}</td></tr>"
        for r in holdings
    ) or '<tr><td colspan="7">보유종목 데이터 확인 필요</td></tr>'
    return f"""
    <section class='box'>
      <h2>보유종목 현재가 현황</h2>
      <div class='tablewrap'><table><thead><tr><th>종목</th><th>코드</th><th>판단</th><th>평균단가</th><th>현재가</th><th>손익률%</th><th>출처</th></tr></thead><tbody>{rows}</tbody></table></div>
    </section>
    """

def ai_section():
    ai = read_csv('docs/data/latest_holding_ai_briefing.csv')
    cards = ''
    for r in ai[:5]:
        summary = r.get('ai_issue_summary') or r.get('ai_summary') or r.get('issue_overview') or ''
        action = r.get('ai_action_guide') or r.get('action_comment') or ''
        model = r.get('gemini_model_used') or ''
        cards += (
            f"<article class='card'><h3>{esc(r.get('stock_name'))} <span>{esc(r.get('ai_status'))} {esc(model)}</span></h3>"
            f"<p>{esc(summary)}</p>"
            f"<p><b>대응:</b> {esc(action)}</p></article>"
        )
    if not cards:
        cards = '<article class="card"><h3>Gemini AI 브리핑</h3><p>데이터 확인 필요</p></article>'
    return f"<section><h2>Gemini AI 보유 브리핑</h2>{cards}</section>"

def news_section():
    news = read_csv('docs/data/latest_news_detail.csv', 8)
    items = ''.join(
        f"<li><a href='{esc(r.get('link'))}' target='_blank' rel='noopener'>{esc(r.get('title'))}</a><br>"
        f"<span>{esc(r.get('description'))}</span></li>"
        for r in news if r.get('title')
    ) or '<li>뉴스 데이터 확인 필요</li>'
    return f"<section class='box'><h2>네이버뉴스 상세 일부</h2><ul>{items}</ul></section>"

def latest_html(stamp, ss):
    return f"""<!doctype html>
<html lang='ko'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Stock Report Latest</title>
<style>
body{{margin:0;background:#f6f7fb;color:#111827;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}
.wrap{{max-width:1120px;margin:auto;padding:20px}}
.hero{{background:#111827;color:white;border-radius:22px;padding:22px;margin-bottom:16px}}
.hero p{{color:#d1d5db}}
.links{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px;margin-bottom:16px}}
.link,.mini-links a{{background:white;border-radius:16px;padding:14px;text-decoration:none;color:#111827;box-shadow:0 4px 16px #0001;font-weight:700}}
.mini-links{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px;margin-top:10px}}
.box,.card{{background:white;border-radius:18px;padding:16px;margin-bottom:16px;box-shadow:0 4px 16px #0001}}.downloads{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px}}.download{{display:flex;flex-direction:column;gap:5px;background:#f8fafc;border:1px solid #e5e7eb;border-radius:14px;padding:14px;text-decoration:none;color:#111827}}.download span{{color:#2563eb;font-weight:700}}.download small{{font-size:12px;color:#6b7280;line-height:1.4}}
.accent{{border:1px solid #dbeafe;background:#f8fbff}}
.tablewrap{{overflow:auto}}
table{{border-collapse:collapse;width:100%;min-width:900px}}
th,td{{border-bottom:1px solid #e5e7eb;padding:9px;font-size:13px;text-align:left;vertical-align:top}}
th{{background:#f3f4f6}}
h2{{margin:0 0 10px}} h3{{margin:0 0 8px}}
p,li,.hint{{font-size:14px;line-height:1.65;color:#374151}}
a{{color:#2563eb;text-decoration:none}}
.card span{{font-size:12px;color:#6b7280;font-weight:500}}
</style>
</head>
<body>
<main class='wrap'>
<section class='hero'>
<h1>최신 주식 리포트</h1>
<p>갱신: {esc(stamp)} · 세션: {esc(ss)}<br>추천후보, 전략검증, 보유종목, Gemini AI 브리핑을 최신 CSV 데이터 기준으로 함께 보여줍니다.</p>
</section>
<section class='links'>
<a class='link' href='../details/candidate_detail.html'>추천후보 상세</a>
<a class='link' href='../details/continuous.html'>연속추천/관찰</a>
<a class='link' href='../strategy/'>전략검증</a>
<a class='link' href='../v11_holdings/'>보유종목 상세</a>
<a class='link' href='../details/holding_ai_briefing.html'>Gemini AI 브리핑</a>
<a class='link' href='../details/naver_news.html'>네이버뉴스 상세</a>
</section>
{download_section()}
{recommendation_section()}
{strategy_section()}
{holdings_section()}
{ai_section()}
{news_section()}
</main>
<!-- latest-refresh: {esc(stamp)} / {esc(ss)} -->
</body>
</html>"""

def write_mobile(stamp, ss):
    links = [
        ('최신 리포트', '../latest/'),
        ('엑셀/상세파일 다운로드', '../downloads/'),
        ('최신 엑셀 바로받기', '../downloads/latest_stock_report.xlsx'),
        ('추천후보 상세', '../details/candidate_detail.html'),
        ('연속추천/관찰', '../details/continuous.html'),
        ('전략검증', '../strategy/'),
        ('보유종목', '../v11_holdings/'),
        ('Gemini AI 브리핑', '../details/holding_ai_briefing.html'),
        ('네이버뉴스', '../details/naver_news.html'),
        ('리스크 규칙', '../details/risk_rules.html'),
    ]
    cards = ''.join(f"<a class='card' href='{u}'><b>{t}</b><span>열기</span></a>" for t, u in links)
    Path('docs/mobile/index.html').write_text(f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><style>body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f6f7fb;margin:0}}.wrap{{max-width:860px;margin:auto;padding:20px}}.hero{{background:#111827;color:white;border-radius:22px;padding:22px}}.hero p{{color:#d1d5db;line-height:1.55}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin-top:14px}}.card{{display:flex;justify-content:space-between;text-decoration:none;color:#111827;background:white;border-radius:18px;padding:18px;box-shadow:0 4px 16px #0001}}</style></head><body><main class='wrap'><section class='hero'><h1>주식 리포트 모바일 홈</h1><p>최근 갱신: {esc(stamp)}<br>세션: {esc(ss)}<br>추천후보·전략검증·보유종목·AI브리핑을 함께 확인합니다.</p></section><section class='grid'>{cards}</section></main></body></html>""", encoding='utf-8')

def main():
    stamp, ss = now(), session()
    Path('docs/latest').mkdir(parents=True, exist_ok=True)
    Path('docs/mobile').mkdir(parents=True, exist_ok=True)
    Path('docs/data').mkdir(parents=True, exist_ok=True)

    Path('docs/latest/index.html').write_text(latest_html(stamp, ss), encoding='utf-8')
    write_mobile(stamp, ss)
    Path('docs/data/latest_publish_status.csv').write_text(f'key,value\npublished_at,{stamp}\nsession,{ss}\nsource,clean_latest_dashboard_v12_2_2\n', encoding='utf-8-sig')
    print('✅ clean latest dashboard rebuilt with recommendation interface')
    print('✅ mobile dashboard rebuilt with recommendation links')
    print('✅ latest publish status csv written')

if __name__ == '__main__':
    main()
