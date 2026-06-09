#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone, timedelta
import csv, html, re, shutil
import pandas as pd

from stock_news_disambiguation import filter_and_rank_news, normalize_category as _normalize_category, stock_basic_info as _stock_basic_info

KST = timezone(timedelta(hours=9))
SHEET_MAP = {
    "모바일_대시보드": "legacy_mobile_dashboard", "TOP후보_요약": "legacy_top_candidates",
    "추천 리스트": "legacy_full_recommendations", "진입시나리오": "legacy_entry_scenario",
    "진입가이드_요약": "legacy_entry_guide", "연속추천_관찰": "legacy_continuous",
    "종목카드_TOP15": "legacy_stock_cards_top15", "추천성과_검증": "legacy_recommendation_performance",
    "전략백테스트요약": "legacy_strategy_backtest_summary", "계좌백테스트요약": "legacy_account_backtest_summary",
    "백테스트검증가이드": "legacy_backtest_validation_guide", "보유종목_판단": "legacy_holding_decision", "시장상태": "legacy_market_state",
}
ETF_BRANDS = ["KODEX", "TIGER", "RISE", "SOL", "ACE", "KBSTAR", "TIMEFOLIO", "HANARO", "ARIRANG", "PLUS", "KoAct"]
NEWS_BLACKLIST = {"태웅": ["태웅식품", "태웅로직스", "태웅푸드"]}

def now(): return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")
def esc(x): return html.escape(str(x if x is not None else ""))
def clean_value(x):
    if x is None: return ""
    try:
        if isinstance(x, float) and pd.isna(x): return ""
    except Exception: pass
    s = str(x).strip()
    return "" if s.lower() in {"nan","none","nat"} else s

def find_latest_xlsx() -> Path | None:
    files, seen = [], set()
    for root in [Path('.'), Path('stock_report'), Path('docs')]:
        if not root.exists(): continue
        for p in root.rglob('*.xlsx'):
            if not p.is_file(): continue
            text = p.as_posix()
            if 'docs/downloads' in text or '__MACOSX' in text: continue
            key = p.resolve()
            if key in seen: continue
            seen.add(key); files.append(p)
    if not files: return None
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0]

def normalize_columns(cols):
    out, seen = [], {}
    for c in cols:
        name = clean_value(c) or '컬럼'
        if name in seen:
            seen[name] += 1; name = f"{name}_{seen[name]}"
        else: seen[name] = 1
        out.append(name)
    return out

def read_sheet_table(xlsx: Path, sheet_name: str) -> pd.DataFrame:
    try: raw = pd.read_excel(xlsx, sheet_name=sheet_name, header=None, dtype=object)
    except Exception: return pd.DataFrame()
    if raw.empty: return pd.DataFrame()
    header_row = None
    for idx in range(min(len(raw), 25)):
        vals = [clean_value(v) for v in raw.iloc[idx].tolist()]
        non_empty = [v for v in vals if v]
        if len(non_empty) < 2: continue
        score = sum(1 for v in non_empty if any(k in v for k in ['순위','종목','시장','섹터','후보','현재가','점수','진입','손절','익절','전략','수익','상태','주목']))
        if score >= 2:
            header_row = idx; break
    if header_row is None: header_row = 0
    header = normalize_columns(raw.iloc[header_row].tolist())
    df = raw.iloc[header_row + 1:].copy(); df.columns = header
    df = df.dropna(how='all').applymap(clean_value)
    empty_cols = [c for c in df.columns if not c or str(c).startswith('Unnamed')]
    return df.drop(columns=empty_cols, errors='ignore')

def write_df(df: pd.DataFrame, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding='utf-8-sig')

def read_csv_rows(path: str | Path, limit=999):
    p = Path(path)
    if not p.exists(): return []
    for enc in ['utf-8-sig','utf-8','cp949','euc-kr']:
        try:
            with p.open(encoding=enc, newline='') as f: return list(csv.DictReader(f))[:limit]
        except Exception: pass
    return []

def pick(row, names):
    if not row: return ''
    lower = {str(k).strip().lower(): k for k in row.keys()}
    for name in names:
        k = lower.get(name.lower())
        if k and clean_value(row.get(k)): return clean_value(row.get(k))
    for k, v in row.items():
        kk = str(k).lower()
        for name in names:
            if name.lower() in kk and clean_value(v): return clean_value(v)
    return ''

def is_etf(name: str) -> bool:
    upper = (name or '').upper()
    return any(brand.upper() in upper for brand in ETF_BRANDS)

def etf_theme(name: str) -> str:
    n = name or ''
    mapping = [
        ('미국 S&P500', ['S&P500','S＆P500','미국S&P']), ('미국 배당/다우존스', ['미국배당','다우존스','SCHD']),
        ('2차전지', ['2차전지','배터리']), ('AI·로봇', ['AI','로봇']), ('반도체', ['반도체','전공정','후공정']),
        ('커버드콜/인컴', ['커버드콜','월배당','배당커버드콜']), ('채권/혼합', ['미국채','채권','혼합']), ('그룹주', ['그룹']), ('배당', ['배당'])]
    for label, words in mapping:
        if any(w in n for w in words): return label
    return 'ETF'

def industry_from_text(text: str) -> str:
    rules = [('반도체/IT부품',['반도체','HBM','메모리','파운드리','디스플레이','PCB','전자부품']),('2차전지/전기차',['2차전지','배터리','전기차','양극재','음극재','리튬']),('바이오/헬스케어',['바이오','제약','신약','의료','헬스케어','임상']),('방산/우주항공',['방산','무기','항공','우주','위성','드론']),('조선/기계',['조선','선박','기계','플랜트','중공업']),('자동차/부품',['자동차','모빌리티','타이어']),('AI/소프트웨어',['AI','인공지능','소프트웨어','클라우드','데이터센터','보안']),('금융/지주',['은행','금융','보험','증권','지주','창투','벤처']),('통신/미디어/콘텐츠',['통신','플랫폼','콘텐츠','게임','미디어','방송']),('철강/소재/화학',['철강','화학','소재','정유','석유','에너지']),('소비재/유통',['유통','식품','화장품','의류','소비재']),('건설/인프라',['건설','인프라','부동산','시멘트'])]
    low = (text or '').lower()
    for label, words in rules:
        if any(w.lower() in low for w in words): return label
    return ''

def normalize_category(name: str, sector: str, reason: str = '') -> str:
    if is_etf(name): return f"ETF · {etf_theme(name)}"
    return industry_from_text(' '.join([name or '', sector or '', reason or ''])) or sector or '분야 확인 필요'

def strict_name_match(text: str, name: str) -> bool:
    if not name: return False
    if any(bad in text for bad in NEWS_BLACKLIST.get(name, [])): return False
    if name not in text: return False
    for suffix in ['식품','푸드','로직스','바이오','제약']:
        if len(name) <= 3 and name + suffix in text: return False
    return True

def related_news(news_rows, name, limit=4):
    if not name: return []
    toks = [t for t in re.split(r'[\s/·,_\-\(\)\[\]]+', name) if len(t) >= 2]
    scored = []
    for r in news_rows:
        title = clean_value(pick(r, ['title','제목'])); desc = clean_value(pick(r, ['description','요약','본문'])); query = pick(r, ['query','검색어'])
        text = f"{query} {title} {desc}"
        if not strict_name_match(text, name) and query != name: continue
        if any(bad in text for bad in NEWS_BLACKLIST.get(name, [])): continue
        score = (8 if query == name else 0) + (8 if strict_name_match(text, name) else 0) + sum(1 for t in toks if t in text)
        if score: scored.append((score, {'title': title or '제목 없음', 'desc': desc, 'link': pick(r, ['link','링크'])}))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [x[1] for x in scored[:limit]]

def stock_basic_info(name, sector, reason='', price='', score='', entry='', news_links=None):
    news_links = news_links or []
    category = normalize_category(name, sector, reason)
    if is_etf(name):
        line1 = f"{name}은(는) 개별 기업이 아니라 {etf_theme(name)} 테마의 ETF입니다."
        line2 = '주요 확인 포인트는 구성 자산, 추종 지수, 환율 영향, 분배금/커버드콜 여부입니다.'
    else:
        line1 = f"{name}은(는) {category} 흐름과 연결해서 볼 수 있는 종목입니다."
        line2 = '주요 확인 포인트는 최근 실적, 수급, 공시, 업종 모멘텀입니다.'
    score_part = f" 현재가 {price}, 실전점수 {score}, 진입판정은 '{entry}'입니다." if (price or score or entry) else ''
    line3 = f"최근 연결 뉴스는 '{news_links[0]['title'][:80]}' 중심이며, 동일명이 아닌 다른 회사 뉴스가 섞이지 않았는지 필터링했습니다." if news_links else '연결 뉴스가 부족하면 뉴스보다 가격 위치, 거래량, 재등장 여부를 우선 확인하는 편이 좋습니다.'
    return f"{line1} {line2}{score_part} {line3}".strip()


# --- v12.2.11 general news disambiguation engine overrides ---
def normalize_category(name: str, sector: str, reason: str = '') -> str:
    return _normalize_category(name, sector, reason)

def related_news(news_rows, name, limit=4):
    if isinstance(limit, str):
        stock_code = limit
        limit = 4
    else:
        stock_code = ''
    return filter_and_rank_news(name, stock_code, news_rows, limit=limit)

def stock_basic_info(name, sector, reason='', price='', score='', entry='', news_links=None):
    return _stock_basic_info(name, sector, reason, price, score, entry, news_links or [])

def reorder_headers(rows, fixed_priority=None):
    if not rows: return []
    all_headers = []
    for r in rows:
        for k in r.keys():
            if k not in all_headers: all_headers.append(k)
    fixed_priority = fixed_priority or []
    fixed = [h for h in fixed_priority if h in all_headers]
    toss = [h for h in all_headers if 'toss' in h.lower() or '토스' in h]
    rest = [h for h in all_headers if h not in fixed and h not in toss]
    def density(h): return sum(1 for r in rows if clean_value(r.get(h)))
    rest.sort(key=lambda h: (-density(h), all_headers.index(h)))
    return fixed + rest + toss

def col_width_class(header):
    h = str(header)
    if any(k in h for k in ['상세','가이드','메모','설명','사유','뉴스','계획']): return 'wide'
    if any(k in h for k in ['종목명','섹터','분야','후보출처']): return 'mid'
    return 'narrow'

def table_html(rows, headers=None, max_rows=60):
    rows = rows[:max_rows]
    if not rows: return "<p class='hint'>표시할 데이터가 없습니다.</p>"
    headers = headers or reorder_headers(rows)
    colgroup = ''.join(f"<col style='min-width:{'430px' if col_width_class(h)=='wide' else '150px' if col_width_class(h)=='mid' else '92px'};width:{'430px' if col_width_class(h)=='wide' else '150px' if col_width_class(h)=='mid' else '92px'}'>" for h in headers)
    th = ''.join(f"<th>{esc(h)}</th>" for h in headers)
    body = ''.join('<tr>' + ''.join(f"<td>{esc(r.get(h,''))}</td>" for h in headers) + '</tr>' for r in rows)
    return f"<div class='tablewrap'><table><colgroup>{colgroup}</colgroup><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>"

CSS = """body{margin:0;background:#f6f7fb;color:#111827;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}.wrap{max-width:1080px;margin:auto;padding:20px}.hero{background:#172554;color:white;border-radius:22px;padding:22px;margin-bottom:16px}.hero p{color:#dbeafe;line-height:1.55}.box,.card{background:white;border-radius:18px;padding:16px;margin-bottom:16px;box-shadow:0 4px 16px rgba(0,0,0,.06)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:12px}.card h3{margin:0 0 8px}.pill{display:inline-block;background:#dbeafe;color:#1e40af;border-radius:999px;padding:5px 10px;font-size:12px;font-weight:700}.meta,.hint{font-size:13px;color:#6b7280;line-height:1.55}p,li{font-size:14px;line-height:1.68;color:#374151}.tablewrap{overflow:auto;background:white;border-radius:16px;border:1px solid #e5e7eb}table{border-collapse:collapse;width:max-content;min-width:100%}th,td{border-bottom:1px solid #e5e7eb;padding:10px;font-size:13px;text-align:left;vertical-align:top;white-space:normal;word-break:keep-all}th{background:#f3f4f6;color:#334155}a{color:#2563eb;font-weight:700;text-decoration:none}.links{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px}.links a{display:block;background:#fff;border-radius:16px;padding:14px;box-shadow:0 4px 16px rgba(0,0,0,.06)}"""

def write_page(path: Path, title: str, subtitle: str, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title><style>{CSS}</style></head><body><main class="wrap"><section class="hero"><h1>{esc(title)}</h1><p>{esc(subtitle)}</p></section>{content}</main></body></html>""", encoding='utf-8')

def by_name(rows, names=['종목명','stock_name']): return {pick(r, names): r for r in rows}


def _extract_percent_numbers(text):
    vals = re.findall(r"\+?\d+(?:\.\d+)?\s*%", clean_value(text))
    return [v.replace(' ', '') for v in vals]

def format_tp_plan(raw):
    text = clean_value(raw)
    vals = _extract_percent_numbers(text)
    if len(vals) >= 3:
        return f"<b>{vals[0]}(60)</b> / <b>{vals[1]}(20)</b> / <b>{vals[2]}(20)</b>"
    if len(vals) == 2:
        return f"<b>{vals[0]}(60)</b> / <b>{vals[1]}(40)</b>"
    if len(vals) == 1:
        return f"<b>{vals[0]}</b>"
    return esc(text)

def format_sl_plan(raw):
    text = clean_value(raw)
    vals = _extract_percent_numbers(text)
    if vals:
        return ' / '.join(f"<b>{esc(v)}</b>" for v in vals)
    return esc(text)

def build_top_cards(top_rows, entry_rows, guide_rows, news_rows):
    entry_by, guide_by = by_name(entry_rows), by_name(guide_rows, ['stock_name','종목명'])
    cards = ''
    for r in top_rows[:15]:
        name = pick(r, ['종목명','stock_name']); e = entry_by.get(name, {}); g = guide_by.get(name, {})
        rank = pick(r, ['순위','rank']); sector = pick(r, ['섹터/분야','분야','sector']); score = pick(r, ['실전점수','점수','score','기본점수']); price = pick(r, ['현재가','current_price']); entry_decision = pick(r, ['진입판정','entry_action','entry_guide'])
        news = related_news(news_rows, name, 3)
        basic = stock_basic_info(name, sector, pick(g, ['entry_guide']) or entry_decision, price, score, entry_decision, news)
        cards += f"""<article class="card"><h3>#{esc(rank)} {esc(name)}</h3><div class="meta">{esc(normalize_category(name, sector))} · 현재가 {esc(price)} · 실전점수 {esc(score)}</div><p>{esc(basic)}</p><p><span class="pill">{esc(entry_decision or '진입판정 확인')}</span></p><p><b>공격/기준/보수:</b> {esc(pick(e, ['공격진입가']))} / {esc(pick(e, ['기준진입가']))} / {esc(pick(e, ['보수진입가']))}</p><p><b>돌파/손절:</b> {esc(pick(e, ['돌파진입가']))} / {esc(pick(e, ['손절기준가']))}</p><p><b>익절:</b> {format_tp_plan(pick(r, ['익절계획']) or pick(g, ['take_profit_guide']))}<br><b>손절:</b> {format_sl_plan(pick(r, ['손절계획']) or pick(g, ['stop_loss_guide']))}</p></article>"""
    return f"<section class='grid'>{cards}</section>" if cards else "<p class='hint'>TOP 후보 데이터가 없습니다.</p>"

def build_strategy_summary(strategy_rows, perf_rows, account_rows, guide_rows):
    parts=[]
    if account_rows: parts.append("<section class='box'><h2>계좌 백테스트 요약</h2>" + table_html(account_rows, max_rows=5) + "</section>")
    if perf_rows:
        headers=[h for h in ['recommend_date','session','rank','stock_name','sector','score','recommend_price','latest_price','latest_return_pct','max_observed_return_pct'] if h in perf_rows[0]]
        parts.append("<section class='box'><h2>추천성과 검증</h2>" + table_html(perf_rows, headers=headers, max_rows=30) + "</section>")
    if strategy_rows:
        headers=[h for h in ['종목명','종목코드','TP전략','SL전략','수익률','MDD','승률','거래횟수','백테스트신뢰도'] if h in strategy_rows[0]]
        parts.append("<section class='box'><h2>전략 백테스트 요약</h2>" + table_html(strategy_rows, headers=headers, max_rows=40) + "</section>")
    return ''.join(parts) or "<p class='hint'>전략 검증 데이터가 없습니다.</p>"

def build_news_summary(news_rows):
    good=[r for r in news_rows if pick(r,['title']) and pick(r,['api_state']) in ['ok','']]
    if not good: return '뉴스 데이터가 충분하지 않습니다.'
    words=[]
    for r in good[:8]:
        for token in re.split(r"[\s·,./\[\]\(\)'\"“”]+", pick(r,['title'])):
            token=token.strip()
            if len(token)>=2 and token not in ['뉴스','증시','오늘','관련','종목']: words.append(token)
    freq={}
    for w in words: freq[w]=freq.get(w,0)+1
    top=', '.join([w for w,_ in sorted(freq.items(), key=lambda x:(-x[1],x[0]))[:5]]) or '시장/종목별 이슈'
    return f'주요 뉴스는 {top} 키워드 중심으로 확인됩니다. 뉴스 제목만으로 단정하지 말고 거래량, 공시, 수급, 장중 가격 반응을 함께 확인하는 쪽이 안전합니다.'

def build_outputs():
    data, details = Path('docs/data'), Path('docs/details')
    data.mkdir(parents=True, exist_ok=True); details.mkdir(parents=True, exist_ok=True)
    xlsx=find_latest_xlsx(); status_rows=[{'key':'checked_at','value':now()}]
    if not xlsx:
        status_rows.append({'key':'xlsx','value':'not_found'}); write_df(pd.DataFrame(status_rows), data/'latest_legacy_sections_status.csv'); print('⚠️ legacy restore: xlsx not found'); return
    status_rows.append({'key':'xlsx','value':xlsx.as_posix()}); extracted={}
    for sheet, slug in SHEET_MAP.items():
        df=read_sheet_table(xlsx, sheet)
        if df.empty: status_rows.append({'key':f'sheet_{sheet}','value':'missing_or_empty'}); continue
        write_df(df, data/f'latest_{slug}.csv'); extracted[slug]=df.to_dict('records'); status_rows.append({'key':f'sheet_{sheet}','value':f'ok:{len(df)}'})
    top_rows=extracted.get('legacy_top_candidates',[]); full_rows=extracted.get('legacy_full_recommendations',[]); entry_rows=extracted.get('legacy_entry_scenario',[]); guide_rows=extracted.get('legacy_entry_guide',[]); continuous_rows=extracted.get('legacy_continuous',[]); perf_rows=extracted.get('legacy_recommendation_performance',[]); strategy_rows=extracted.get('legacy_strategy_backtest_summary',[]); account_rows=extracted.get('legacy_account_backtest_summary',[]); validation_rows=extracted.get('legacy_backtest_validation_guide',[]); mobile_rows=extracted.get('legacy_mobile_dashboard',[])
    news_rows=read_csv_rows(data/'latest_news_detail.csv',500); guide_by=by_name(guide_rows,['stock_name','종목명']); entry_by=by_name(entry_rows)
    if top_rows:
        alias=[]
        for r in top_rows:
            name=pick(r,['종목명','stock_name']); g=guide_by.get(name,{}); e=entry_by.get(name,{})
            sector=normalize_category(name,pick(r,['섹터/분야','분야']),pick(g,['entry_guide'])); news=related_news(news_rows,name,3)
            alias.append({'rank':pick(r,['순위']),'stock_name':name,'stock_code':pick(r,['종목코드','stock_code']),'market':pick(r,['시장']),'sector':sector,'source':pick(r,['후보출처']),'current_price':pick(r,['현재가']),'base_score':pick(r,['기본점수']),'score':pick(r,['실전점수','점수']),'overheat':pick(r,['과열판정']),'entry_decision':pick(r,['진입판정']),'attack_entry':pick(e,['공격진입가']),'base_entry':pick(e,['기준진입가']),'conservative_entry':pick(e,['보수진입가']),'breakout_entry':pick(e,['돌파진입가']),'stop_price':pick(e,['손절기준가']),'take_profit_plan':pick(r,['익절계획']) or pick(g,['take_profit_guide']),'stop_loss_plan':pick(r,['손절계획']) or pick(g,['stop_loss_guide']),'entry_guide':pick(g,['entry_guide']),'do_not_chase':pick(g,['do_not_chase']),'check_points':pick(g,['check_points']),'stock_description':stock_basic_info(name,sector,pick(g,['entry_guide']),pick(r,['현재가']),pick(r,['실전점수','점수']),pick(r,['진입판정']),news)})
        write_df(pd.DataFrame(alias), data/'latest_recommendation_top15_full.csv'); write_df(pd.DataFrame(alias), data/'latest_recommendation_analysis.csv')
    write_page(details/'legacy_top15.html','추천 TOP15 + 진입 시나리오',f'원천 파일: {xlsx.as_posix()} · TOP후보_요약/진입시나리오/진입가이드_요약 시트를 함께 보여줍니다.', build_top_cards(top_rows,entry_rows,guide_rows,news_rows)+"<section class='box'><h2>TOP 후보 원본 표</h2>"+table_html(top_rows,max_rows=20)+"</section>")
    full_priority=['순위','종목명','시장','섹터/분야','현재가','기본점수','실전점수','과열판정','진입판정','익절계획','손절계획','추세','백테스트신뢰도','상세전략가이드','entry_guide','take_profit_guide','stop_loss_guide','do_not_chase']
    write_page(details/'legacy_full_recommendations.html','전체 추천 명단 · 기존 엑셀 데이터',f'원천 파일: {xlsx.as_posix()} · 추천 리스트 시트 기반입니다. 비어 있는 TOSS 관련 열은 뒤쪽으로 밀고, 데이터가 많은 열을 앞쪽에 배치했습니다.', table_html(full_rows, headers=reorder_headers(full_rows,full_priority), max_rows=120))
    write_page(details/'legacy_entry_scenario.html','진입 시나리오 · 기존 엑셀 데이터',f'원천 파일: {xlsx.as_posix()} · 진입시나리오/진입가이드_요약 시트를 활용합니다.', build_top_cards(top_rows,entry_rows,guide_rows,news_rows)+"<section class='box'><h2>진입 시나리오 원본 표</h2>"+table_html(entry_rows,max_rows=20)+"</section><section class='box'><h2>진입가이드 요약표</h2>"+table_html(guide_rows,max_rows=20)+"</section>")
    write_page(details/'legacy_continuous.html','연속추천 관찰 · 기존 엑셀 데이터',f'원천 파일: {xlsx.as_posix()} · 연속추천_관찰 시트 기반입니다.', table_html(continuous_rows,max_rows=60))
    write_page(details/'legacy_strategy_validation.html','전략 추천/검증 · 참고용',f'원천 파일: {xlsx.as_posix()} · 필요할 때만 보는 검증 자료입니다.', build_strategy_summary(strategy_rows,perf_rows,account_rows,validation_rows))
    write_page(details/'legacy_mobile_dashboard.html','모바일 대시보드 원본 · 기존 엑셀 데이터',f'원천 파일: {xlsx.as_posix()} · 원본 확인용입니다.', table_html(mobile_rows,max_rows=20))
    shutil.copyfile(details/'legacy_top15.html', details/'recommendation_top15.html'); shutil.copyfile(details/'legacy_full_recommendations.html', details/'recommendation_full_list.html'); shutil.copyfile(details/'legacy_entry_scenario.html', details/'entry_scenario.html'); shutil.copyfile(details/'legacy_continuous.html', details/'continuous.html')
    holding_rows=read_csv_rows(data/'latest_holding_deep_analysis.csv',200); holding_info=[]
    for r in holding_rows:
        name=pick(r,['stock_name','종목명']); decision=pick(r,['decision','판단']); price=pick(r,['current_price','현재가']); pnl=pick(r,['unrealized_pnl_pct','손익률']); news=related_news(news_rows,name,3)
        holding_info.append({'stock_name':name,'stock_code':pick(r,['stock_code','종목코드']),'decision':decision,'current_price':price,'pnl_pct':pnl,'stock_description':stock_basic_info(name,'',decision,price,'',decision,news),'news_match_note':'strict_name_filter_applied','checked_at':now()})
    if holding_info: write_df(pd.DataFrame(holding_info), data/'latest_holding_stock_descriptions.csv')
    write_df(pd.DataFrame([{'summary':build_news_summary(news_rows),'checked_at':now()}]), data/'latest_major_news_summary.csv')

    write_page(
        details/'legacy_candidate_dashboard_validation.html',
        '추천후보 대시보드 + 검증',
        f'원천 파일: {xlsx.as_posix()} · 추천후보 대시보드와 전략검증을 한 페이지로 묶었습니다.',
        "<section class='box'><h2>추천후보 대시보드</h2>" + table_html(mobile_rows, max_rows=20) + '</section>' + build_strategy_summary(strategy_rows, perf_rows, account_rows, validation_rows)
    )

    write_df(pd.DataFrame(status_rows), data/'latest_legacy_sections_status.csv')
    print('✅ legacy Excel sections restored and refined'); print(f'xlsx: {xlsx}'); print(f'sheets: {len(extracted)}')
if __name__ == '__main__': build_outputs()
