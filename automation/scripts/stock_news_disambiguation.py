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

def stock_basic_info(stock_name: str, sector: str = "", reason: str = "", price: str = "", score: str = "", entry: str = "", news_rows: list[dict] | None = None) -> str:
    news_rows = news_rows or []
    category = normalize_category(stock_name, sector, reason)
    if is_etf_name(stock_name):
        line1=f"{stock_name}은(는) 개별 기업이 아니라 {etf_theme(stock_name)} 테마의 ETF입니다."
        line2="주요 확인 포인트는 추종 지수, 구성 종목, 환율 영향, 분배금/커버드콜 여부입니다."
    else:
        line1=f"{stock_name}은(는) {category} 흐름과 연결해서 볼 수 있는 종목입니다."
        line2="주요 확인 포인트는 최근 실적, 수급, 공시, 업종 모멘텀입니다."
    if price or score or entry: line2 += f" 현재가 {price}, 실전점수 {score}, 진입판정은 '{entry}'입니다."
    if news_rows:
        title=strip_html(news_rows[0].get("title") or news_rows[0].get("제목") or "")[:90]
        line3=f"최근 연결 뉴스는 '{title}' 중심이며, 종목명 오매칭 필터를 통과한 기사만 표시합니다."
    else:
        line3="연결 뉴스가 부족하면 뉴스보다 가격 위치, 거래량, 재등장 여부를 우선 확인하는 편이 좋습니다."
    return " ".join([line1,line2,line3]).strip()
