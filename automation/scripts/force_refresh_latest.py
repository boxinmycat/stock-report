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

def table_html(rows, headers=None, max_rows=20):
    rows = rows[:max_rows]
    if not rows:
        return "<p class='hint'>데이터 확인 필요</p>"
    if not headers:
        headers = []
        for r in rows:
            for k in r.keys():
                if k not in headers:
                    headers.append(k)
    th = ''.join(f"<th>{esc(h)}</th>" for h in headers)
    body = ''
    for r in rows:
        body += '<tr>' + ''.join(f"<td>{esc(r.get(h,''))}</td>" for h in headers) + '</tr>'
    return f"<div class='tablewrap'><table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>"

def status_dict():
    d = {}
    for r in read_csv('docs/data/latest_legacy_sections_status.csv'):
        if r.get('key'):
            d[r['key']] = r.get('value','')
    return d

def download_section():
    downloads = read_csv('docs/data/latest_downloads.csv', 10)
    if not downloads:
        return """<section class='box'><h2>엑셀/상세파일 다운로드</h2><p class='hint'>아직 다운로드 파일이 생성되지 않았습니다.</p></section>"""
    cards = ''
    for r in downloads[:6]:
        label = pick(r, ['label', '파일명'])
        url = pick(r, ['url'])
        size = pick(r, ['size_kb'])
        source = pick(r, ['source'])
        href = '../downloads/' + url.replace('./', '') if url else '../downloads/'
        cards += f"<a class='download' href='{esc(href)}' download><b>{esc(label)}</b><span>{esc(size)} KB</span><small>{esc(source)}</small></a>"
    return f"<section class='box download-box'><h2>엑셀/상세파일 다운로드</h2><p class='hint'>세밀하게 보고 싶을 때는 최신 엑셀 리포트를 내려받아 확인하세요.</p><div class='downloads'>{cards}</div><p class='hint'><a href='../downloads/'>다운로드 센터 전체 보기</a></p></section>"

def legacy_summary_section():
    st = status_dict()
    xlsx = st.get('xlsx', 'not_found')
    return f"""<section class='box accent'>
<h2>기존 엑셀 데이터 복원 상태</h2>
<p class='hint'>이번 페이지는 새로 추정 생성한 추천 분석이 아니라, 리포트 엑셀 안에 이미 있던 시트 데이터를 우선 사용합니다.</p>
<p><b>원천 엑셀:</b> {esc(xlsx)}</p>
<div class='mini-links'>
<a href='../details/legacy_top15.html'>TOP15 원본</a>
<a href='../details/legacy_full_recommendations.html'>전체 추천 명단</a>
<a href='../details/legacy_entry_scenario.html'>진입 시나리오</a>
<a href='../details/legacy_continuous.html'>연속추천 관찰</a>
<a href='../details/legacy_strategy_validation.html'>전략 추천/검증</a>
</div>
</section>"""

def legacy_top15_section():
    rows = read_csv('docs/data/latest_recommendation_top15_full.csv', 15)
    if not rows:
        return "<section class='box accent'><h2>추천 TOP15</h2><p class='hint'>TOP후보_요약 데이터 확인 필요</p></section>"
    cards = ''
    for r in rows[:6]:
        cards += f"""<article class='card'>
<h3>{esc(r.get('rank'))}. {esc(r.get('stock_name'))} <span>{esc(r.get('score'))}</span></h3>
<p class='meta'>{esc(r.get('sector'))} · 현재가 {esc(r.get('current_price'))} · {esc(r.get('entry_decision'))}</p>
<p><b>어떤 종목인가:</b> {esc(r.get('stock_description'))}</p>
<p><b>진입:</b> {esc(r.get('entry_guide'))}</p>
<p><b>익절/손절:</b> {esc(r.get('take_profit_plan'))} / {esc(r.get('stop_loss_plan'))}</p>
</article>"""
    return f"<section class='box accent'><h2>추천 TOP15 미리보기</h2><p class='hint'>TOP후보_요약과 진입가이드_요약 시트 기반입니다.</p><div class='grid'>{cards}</div><div class='mini-links'><a href='../details/legacy_top15.html'>TOP15 상세</a><a href='../details/legacy_full_recommendations.html'>전체 추천 명단</a></div></section>"

def entry_section():
    rows = read_csv('docs/data/latest_legacy_entry_scenario.csv', 15)
    if not rows:
        return ''
    headers = [h for h in ['순위','종목명','섹터/분야','현재가','진입판정','공격진입가','기준진입가','보수진입가','돌파진입가','손절기준가'] if h in rows[0]]
    return f"<section class='box'><h2>진입 시나리오</h2><p class='hint'>진입시나리오 시트의 공격/기준/보수/돌파/손절 가격을 그대로 보여줍니다.</p>{table_html(rows, headers, 15)}<p class='hint'><a href='../details/legacy_entry_scenario.html'>진입 시나리오 전체 보기</a></p></section>"

def continuous_section():
    rows = read_csv('docs/data/latest_legacy_continuous.csv', 20)
    if not rows:
        return ''
    headers = [h for h in ['주목등급','종목명','표시분야','오늘순위','오늘점수','연속추천일수','최근7회추천횟수','최근등장일','판정','메모'] if h in rows[0]]
    return f"<section class='box'><h2>연속추천 관찰</h2><p class='hint'>연속추천_관찰 시트 기반입니다.</p>{table_html(rows, headers, 20)}<p class='hint'><a href='../details/legacy_continuous.html'>연속추천 전체 보기</a></p></section>"

def strategy_section():
    acct = read_csv('docs/data/latest_legacy_account_backtest_summary.csv', 5)
    perf = read_csv('docs/data/latest_legacy_recommendation_performance.csv', 10)
    body = ''
    if acct:
        body += '<h3>계좌 백테스트 요약</h3>' + table_html(acct, max_rows=5)
    if perf:
        headers = [h for h in ['recommend_date','session','rank','stock_name','sector','score','recommend_price','latest_price','latest_return_pct','max_observed_return_pct'] if h in perf[0]]
        body += '<h3>추천성과 검증</h3>' + table_html(perf, headers, 10)
    if not body:
        return ''
    return f"<section class='box'><h2>전략 추천/검증</h2>{body}<p class='hint'><a href='../details/legacy_strategy_validation.html'>전략 추천/검증 전체 보기</a></p></section>"

def holdings_section():
    rows = read_csv('docs/data/latest_holding_deep_analysis.csv', 50)
    if not rows:
        return "<section class='box'><h2>보유종목 현재가 현황</h2><p class='hint'>보유종목 데이터 확인 필요</p></section>"
    headers = [h for h in ['stock_name','stock_code','decision','avg_price','current_price','unrealized_pnl_pct','current_price_source'] if h in rows[0]]
    return f"<section class='box'><h2>보유종목 현재가 현황</h2>{table_html(rows, headers, 30)}</section>"

def ai_section():
    rows = read_csv('docs/data/latest_holding_ai_briefing.csv', 5)
    if not rows:
        return "<section class='box'><h2>Gemini AI 보유 브리핑</h2><p class='hint'>AI 브리핑은 장마감 리포트에서 갱신됩니다.</p></section>"
    cards = ''
    for r in rows[:5]:
        summary = r.get('ai_issue_summary') or r.get('ai_three_line_summary') or ''
        action = r.get('ai_action_guide') or ''
        cards += f"<article class='card'><h3>{esc(r.get('stock_name'))} <span>{esc(r.get('ai_sentiment'))}</span></h3><p>{esc(summary)}</p><p><b>대응:</b> {esc(action)}</p></article>"
    return f"<section class='box'><h2>Gemini AI 보유 브리핑</h2><p class='hint'>AI 브리핑은 장마감 리포트에서 주로 갱신됩니다.</p>{cards}</section>"

def news_section():
    rows = read_csv('docs/data/latest_news_detail.csv', 8)
    if not rows:
        return ''
    items = ''
    for r in rows[:8]:
        if r.get('title'):
            link = r.get('link') or '#'
            items += f"<li><a href='{esc(link)}' target='_blank' rel='noopener'>{esc(r.get('title'))}</a><br><span>{esc(r.get('description'))}</span></li>"
    return f"<section class='box'><h2>네이버뉴스 상세 일부</h2><ul>{items}</ul><p class='hint'><a href='../details/naver_news.html'>네이버뉴스 전체 보기</a></p></section>"

def latest_html(stamp, ss):
    return f"""<!doctype html>
<html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Stock Report Latest</title>
<style>
body{{margin:0;background:#f6f7fb;color:#111827;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}
.wrap{{max-width:1120px;margin:auto;padding:20px}}
.hero{{background:#111827;color:white;border-radius:22px;padding:22px;margin-bottom:16px}}.hero p{{color:#d1d5db;line-height:1.55}}
.links,.mini-links{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px;margin:10px 0 16px}}
.link,.mini-links a{{background:white;border-radius:16px;padding:14px;text-decoration:none;color:#111827;box-shadow:0 4px 16px #0001;font-weight:700}}
.box,.card{{background:white;border-radius:18px;padding:16px;margin-bottom:16px;box-shadow:0 4px 16px #0001}}.accent{{border:1px solid #dbeafe;background:#f8fbff}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}}
.downloads{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px}}.download{{display:flex;flex-direction:column;gap:5px;background:#f8fafc;border:1px solid #e5e7eb;border-radius:14px;padding:14px;text-decoration:none;color:#111827}}.download span{{color:#2563eb;font-weight:700}}.download small{{font-size:12px;color:#6b7280;line-height:1.4}}
.tablewrap{{overflow:auto}}table{{border-collapse:collapse;width:100%;min-width:900px}}th,td{{border-bottom:1px solid #e5e7eb;padding:9px;font-size:13px;text-align:left;vertical-align:top}}th{{background:#f3f4f6}}
h2{{margin:0 0 10px}} h3{{margin:12px 0 8px}}p,li,.hint{{font-size:14px;line-height:1.65;color:#374151}}a{{color:#2563eb;text-decoration:none}}.card span{{font-size:12px;color:#6b7280;font-weight:500}}
</style></head><body><main class='wrap'>
<section class='hero'><h1>최신 주식 리포트</h1><p>갱신: {esc(stamp)} · 세션: {esc(ss)}<br>기존 엑셀 리포트의 TOP15·전체추천·진입시나리오·연속추천·전략검증 데이터를 우선 복원하고, 보유종목/AI/뉴스/엑셀 다운로드를 함께 보여줍니다.</p></section>
<section class='links'>
<a class='link' href='../details/legacy_top15.html'>추천 TOP15</a>
<a class='link' href='../details/legacy_full_recommendations.html'>전체 추천 명단</a>
<a class='link' href='../details/legacy_entry_scenario.html'>진입 시나리오</a>
<a class='link' href='../details/legacy_continuous.html'>연속추천 관찰</a>
<a class='link' href='../details/legacy_strategy_validation.html'>전략 추천/검증</a>
<a class='link' href='../v11_holdings/'>보유종목 상세</a>
<a class='link' href='../details/holding_ai_briefing.html'>Gemini AI 브리핑</a>
<a class='link' href='../downloads/'>엑셀 다운로드</a>
</section>
{download_section()}
{legacy_summary_section()}
{legacy_top15_section()}
{entry_section()}
{continuous_section()}
{strategy_section()}
{holdings_section()}
{ai_section()}
{news_section()}
</main><!-- latest-refresh: {esc(stamp)} / {esc(ss)} --></body></html>"""

def write_mobile(stamp, ss):
    groups = [
        ("추천 종목", [
            ("추천 TOP15", "../details/legacy_top15.html"),
            ("전체 추천 명단", "../details/legacy_full_recommendations.html"),
            ("진입 시나리오", "../details/legacy_entry_scenario.html"),
            ("연속추천 관찰", "../details/legacy_continuous.html"),
            ("전략 추천/검증", "../details/legacy_strategy_validation.html"),
            ("원본 모바일 대시보드", "../details/legacy_mobile_dashboard.html"),
        ]),
        ("보유 종목", [
            ("보유종목 상세", "../v11_holdings/"),
            ("보유종목 AI 브리핑", "../details/holding_ai_briefing.html"),
            ("기존 보유종목 판단", "../details/legacy_holding_decision.html"),
        ]),
        ("뉴스/자료", [
            ("네이버뉴스 상세", "../details/naver_news.html"),
            ("엑셀 다운로드 센터", "../downloads/"),
            ("최신 엑셀 바로받기", "../downloads/latest_stock_report.xlsx"),
            ("최신 리포트", "../latest/"),
        ]),
    ]
    sections = ""
    for title, links in groups:
        cards = "".join(f"<a class='card' href='{url}'><b>{label}</b><span>열기</span></a>" for label, url in links)
        sections += f"<section class='group'><h2>{title}</h2><div class='grid'>{cards}</div></section>"
    Path('docs/mobile/index.html').write_text(f"""<!doctype html>
<html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f6f7fb;margin:0;color:#111827}}
.wrap{{max-width:860px;margin:auto;padding:20px}}.hero{{background:#111827;color:white;border-radius:22px;padding:22px;margin-bottom:16px}}.hero p{{color:#d1d5db;line-height:1.55}}
.group{{margin:18px 0}}.group h2{{font-size:18px;margin:0 0 10px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}}
.card{{display:flex;justify-content:space-between;gap:12px;text-decoration:none;color:#111827;background:white;border-radius:18px;padding:18px;box-shadow:0 4px 16px #0001}}.card span{{color:#2563eb;font-weight:700}}
</style></head><body><main class='wrap'><section class='hero'><h1>주식 리포트 모바일 홈</h1><p>최근 갱신: {esc(stamp)}<br>세션: {esc(ss)}<br>기존 엑셀 리포트의 추천 TOP15·전체 추천·진입시나리오·전략검증 메뉴를 복원했습니다.</p></section>{sections}</main></body></html>""", encoding='utf-8')

def main():
    stamp, ss = now(), session()
    Path('docs/latest').mkdir(parents=True, exist_ok=True)
    Path('docs/mobile').mkdir(parents=True, exist_ok=True)
    Path('docs/data').mkdir(parents=True, exist_ok=True)
    Path('docs/latest/index.html').write_text(latest_html(stamp, ss), encoding='utf-8')
    write_mobile(stamp, ss)
    Path('docs/data/latest_publish_status.csv').write_text(f'key,value\npublished_at,{stamp}\nsession,{ss}\nsource,legacy_excel_restore_v12_2_8\n', encoding='utf-8-sig')
    print('✅ clean latest dashboard rebuilt from legacy Excel data')
    print('✅ mobile dashboard rebuilt with legacy recommendation menu')
    print('✅ latest publish status csv written')

if __name__ == '__main__':
    main()
