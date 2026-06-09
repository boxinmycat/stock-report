#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import re, html
from dataclasses import dataclass

ETF_BRANDS = ["KODEX","TIGER","RISE","SOL","ACE","KBSTAR","TIMEFOLIO","HANARO","ARIRANG","PLUS","KoAct","KOSEF","FOCUS"]
AMBIGUOUS_SUFFIXES = ["식품","푸드","로직스","물류","바이오","제약","헬스케어","건설","산업","화학","에너지","테크","솔루션","시스템","홀딩스","그룹","전자","전기","금속","기계","상사","컴퍼니","엔터","엔터테인먼트"]
KNOWN_EXCLUDES = {"태웅": ["태웅식품", "태웅로직스", "태웅푸드"]}
STOCK_CONTEXT_WORDS = ["주가","증시","코스피","코스닥","상장","공시","실적","영업이익","매출","수급","기관","외국인","목표가","투자의견","급등","급락","상승","하락","거래량","시총","배당","분기","반기","사업보고서"]
ETF_CONTEXT_WORDS = ["ETF","상장지수펀드","순자산","분배금","커버드콜","월배당","추종","지수","S&P500","나스닥","미국채","국채","채권","구성종목","리밸런싱"]
INDUSTRY_RULES = [
    ("반도체/IT부품", ["반도체","HBM","메모리","파운드리","디스플레이","PCB","전자부품"]),
    ("2차전지/전기차", ["2차전지","배터리","전기차","양극재","음극재","리튬"]),
    ("바이오/헬스케어", ["바이오","제약","신약","의료","헬스케어","임상"]),
    ("방산/우주항공", ["방산","무기","항공","우주","위성","드론"]),
    ("조선/기계", ["조선","선박","기계","플랜트","중공업"]),
    ("자동차/부품", ["자동차","모빌리티","타이어"]),
    ("AI/소프트웨어", ["AI","인공지능","소프트웨어","클라우드","데이터센터","보안"]),
    ("금융/지주", ["은행","금융","보험","증권","지주","창투","벤처"]),
    ("통신/미디어/콘텐츠", ["통신","플랫폼","콘텐츠","게임","미디어","방송"]),
    ("철강/소재/화학", ["철강","화학","소재","정유","석유","에너지"]),
    ("소비재/유통", ["유통","식품","화장품","의류","소비재"]),
    ("건설/인프라", ["건설","인프라","부동산","시멘트"]),
]
ETF_THEME_RULES = [
    ("미국 S&P500", ["S&P500","S＆P500","미국S&P","미국 S&P"]),
    ("미국 배당/다우존스", ["미국배당","다우존스","SCHD"]),
    ("2차전지", ["2차전지","배터리"]),
    ("AI·로봇", ["AI","로봇"]),
    ("반도체", ["반도체","전공정","후공정"]),
    ("커버드콜/인컴", ["커버드콜","월배당","배당커버드콜"]),
    ("채권/혼합", ["미국채","채권","국채","혼합"]),
    ("그룹주", ["그룹"]),
    ("배당", ["배당"]),
]

def strip_html(value) -> str:
    return re.sub(r"<.*?>", "", html.unescape(str(value or "").strip()))

def is_etf_name(stock_name: str) -> bool:
    upper = (stock_name or "").upper()
    return any(brand.upper() in upper for brand in ETF_BRANDS)

def etf_theme(stock_name: str) -> str:
    name = stock_name or ""
    for label, words in ETF_THEME_RULES:
        if any(word in name for word in words): return label
    return "ETF"

def industry_from_text(text: str) -> str:
    low = (text or "").lower()
    for label, words in INDUSTRY_RULES:
        if any(word.lower() in low for word in words): return label
    return ""

def normalize_category(stock_name: str, sector: str = "", context: str = "") -> str:
    if is_etf_name(stock_name): return f"ETF · {etf_theme(stock_name)}"
    return industry_from_text(" ".join([stock_name or "", sector or "", context or ""])) or sector or "분야 확인 필요"

def tokenise_name(stock_name: str) -> list[str]:
    return [t for t in re.split(r"[\s/·,_\-\(\)\[\]]+", stock_name or "") if len(t) >= 2]

def false_positive_hit(stock_name: str, text: str) -> str:
    if not stock_name: return ""
    for bad in KNOWN_EXCLUDES.get(stock_name, []):
        if bad in text: return bad
    if len(stock_name) <= 3:
        for suffix in AMBIGUOUS_SUFFIXES:
            if stock_name + suffix in text: return stock_name + suffix
    return ""

def build_news_queries(stock_name: str, stock_code: str = "", category: str = "") -> list[str]:
    stock_name = (stock_name or "").strip(); stock_code = (stock_code or "").strip()
    if not stock_name: return []
    if is_etf_name(stock_name):
        base = [f'"{stock_name}" ETF', f'"{stock_name}" 분배금', f'"{stock_name}" 구성종목']
    else:
        base = [f'"{stock_name}" 주식', f'"{stock_name}" 주가', f'"{stock_name}" 실적', f'"{stock_name}" 공시']
        if stock_code: base.insert(1, f'"{stock_name}" {stock_code}')
    out=[]
    for q in base:
        if q not in out: out.append(q)
    return out[:4]

@dataclass
class NewsScore:
    score: int
    accepted: bool
    reason: str

def score_news_match(stock_name: str, stock_code: str, title: str, description: str, query: str = "", category: str = "") -> NewsScore:
    title = strip_html(title); description = strip_html(description); query = strip_html(query)
    text = " ".join([query, title, description])
    bad = false_positive_hit(stock_name, text)
    if bad: return NewsScore(-100, False, f"excluded_false_positive:{bad}")
    if not stock_name: return NewsScore(0, False, "no_stock_name")
    score=0; reasons=[]
    if stock_name in title: score += 8; reasons.append("name_in_title")
    elif stock_name in description: score += 5; reasons.append("name_in_description")
    elif stock_name in query: score += 3; reasons.append("name_in_query")
    if stock_code and stock_code in text: score += 4; reasons.append("code_match")
    hits=sum(1 for t in tokenise_name(stock_name) if t in text); score += hits
    if hits: reasons.append(f"token_hits:{hits}")
    ctx_words = ETF_CONTEXT_WORDS if is_etf_name(stock_name) else STOCK_CONTEXT_WORDS
    ctx=sum(1 for w in ctx_words if w in text); score += min(ctx,4)
    if ctx: reasons.append(f"context:{ctx}")
    if len(stock_name) <= 3 and stock_name not in title and score < 10:
        return NewsScore(score, False, "short_name_weak_match")
    return NewsScore(score, score >= 8, ",".join(reasons) or "weak_match")

def filter_and_rank_news(stock_name: str, stock_code: str, news_rows: list[dict], limit: int = 4) -> list[dict]:
    ranked=[]
    for row in news_rows:
        title = row.get("title") or row.get("제목") or ""
        desc = row.get("description") or row.get("요약") or row.get("본문") or ""
        query = row.get("query") or row.get("검색어") or ""
        ns = score_news_match(stock_name, stock_code, title, desc, query, row.get("category") or "")
        if ns.accepted:
            r=dict(row); r["news_match_score"]=ns.score; r["news_match_reason"]=ns.reason; ranked.append(r)
    ranked.sort(key=lambda r: int(r.get("news_match_score",0)), reverse=True)
    return ranked[:limit]


ETF_DETAIL_MAP = [
    (['미국배당다우존스', '다우존스', 'SCHD'], '미국 배당성장/고배당 컨셉 ETF', '미국 배당성장주와 우량 배당주에 분산 투자하는 상품으로, 대표적으로 코카콜라·펩시코·홈디포·브로드컴·머크 같은 배당 우량주 흐름을 함께 봅니다.'),
    (['S&P500', 'S＆P500', '미국S&P'], '미국 대형주 지수 ETF', '미국 S&P500 지수를 따라가는 상품으로, 애플·마이크로소프트·엔비디아·아마존·알파벳 같은 미국 대형주 비중을 함께 봅니다.'),
    (['2차전지'], '2차전지 테마 ETF', '국내 2차전지 밸류체인에 투자하는 상품으로, 배터리 셀·소재·장비 기업 흐름과 전기차 수요, 리튬 가격 영향을 함께 봅니다.'),
    (['AI', '로봇'], 'AI·로봇 테마 ETF', 'AI 인프라, 로봇 자동화, 반도체·소프트웨어 관련 기업에 분산 투자하는 테마형 ETF입니다.'),
    (['반도체', '전공정', '후공정'], '반도체 테마 ETF', '반도체 장비·소재·설계·제조 밸류체인 흐름을 보는 상품입니다. 업황 사이클과 대형 반도체주 수급이 중요합니다.'),
    (['커버드콜', '월배당', '배당커버드콜'], '커버드콜/인컴 ETF', '주가 상승분 일부를 옵션 프리미엄과 분배금으로 바꾸는 성격이 있어, 강한 상승장에서는 수익이 제한될 수 있습니다.'),
    (['미국채', '국채', '채권', '혼합'], '채권/혼합형 ETF', '주식과 채권 또는 미국 국채 흐름을 함께 반영하는 상품입니다. 금리, 환율, 주식시장 변동성을 같이 봅니다.'),
    (['LG그룹', '그룹플러스'], '그룹주 ETF', '특정 그룹 계열사에 분산 투자하는 상품으로, 대표 계열사의 실적·지배구조·수급 영향을 함께 봅니다.'),
]

def etf_detail(stock_name: str) -> tuple[str, str]:
    name = stock_name or ''
    for keys, label, desc in ETF_DETAIL_MAP:
        if any(k in name for k in keys):
            return label, desc
    return 'ETF 상품', '개별 기업이 아니라 여러 종목을 묶은 상장지수펀드입니다. 추종 지수, 구성종목, 분배금 정책을 함께 확인합니다.'

def company_detail(stock_name: str, category: str, reason: str = '') -> str:
    text = ' '.join([stock_name or '', category or '', reason or ''])
    if '창투' in text or '벤처' in text or '컴퍼니케이' in text:
        return '벤처캐피털/창투사 성격의 기업으로, 투자 회수 성과와 벤처투자 시장 분위기에 영향을 받습니다.'
    if '미디어' in text or '콘텐츠' in text or '헬로비전' in text:
        return '방송·통신·미디어 관련 기업으로, 가입자 기반, 콘텐츠 경쟁력, 통신/미디어 업황을 함께 봅니다.'
    if '디스플레이' in text:
        return '디스플레이 패널 관련 기업으로, LCD/OLED 업황, 고객사 수요, 패널 가격 흐름이 중요합니다.'
    if '반도체' in text or '하이텍' in text:
        return '반도체·전자부품 흐름과 연결되는 종목으로, 업황 사이클과 주요 고객사 수요를 함께 봅니다.'
    if '고무' in text or '플라스틱' in text or '산업' in text:
        return '소재/산업재 성격의 종목으로, 원재료 가격과 전방산업 수요, 실적 안정성을 같이 확인합니다.'
    return f'{category} 관련 종목으로, 최근 실적·공시·수급·업종 모멘텀을 함께 확인하는 편이 좋습니다.'


def stock_basic_info(stock_name: str, sector: str = "", reason: str = "", price: str = "", score: str = "", entry: str = "", news_rows: list[dict] | None = None) -> str:
    news_rows = news_rows or []
    category = normalize_category(stock_name, sector, reason)

    if is_etf_name(stock_name):
        label, desc = etf_detail(stock_name)
        line1 = f"{stock_name}은(는) {label}입니다. {desc}"
    else:
        detail = company_detail(stock_name, category, reason)
        line1 = f"{stock_name}은(는) {category} 흐름과 연결해서 보는 종목입니다. {detail}"

    line2_parts = []
    if price:
        line2_parts.append(f"현재가 {price}")
    if score:
        line2_parts.append(f"실전점수 {score}")
    if entry:
        line2_parts.append(f"진입판정 '{entry}'")
    line2 = " · ".join(line2_parts)

    if news_rows:
        title = strip_html(news_rows[0].get("title") or news_rows[0].get("제목") or "")[:90]
        line3 = f"최근 연결 뉴스는 '{title}' 중심이며, 종목명 오매칭 필터를 통과한 기사만 표시합니다."
    else:
        line3 = "직접 연결 뉴스가 부족하면 가격 위치, 거래량, 재등장 여부를 우선 확인하는 편이 좋습니다."

    return " ".join([x for x in [line1, line2, line3] if x]).strip()
