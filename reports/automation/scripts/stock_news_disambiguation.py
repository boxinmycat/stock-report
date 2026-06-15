#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import re, html
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

KST = timezone(timedelta(hours=9))

ETF_BRANDS = ["KODEX","TIGER","RISE","SOL","ACE","KBSTAR","TIMEFOLIO","HANARO","ARIRANG","PLUS","KoAct","KOSEF","FOCUS"]
AMBIGUOUS_SUFFIXES = ["식품","푸드","로직스","물류","바이오","제약","헬스케어","건설","산업","화학","에너지","테크","솔루션","시스템","홀딩스","그룹","전자","전기","금속","기계","상사","컴퍼니","엔터","엔터테인먼트"]
KNOWN_EXCLUDES = {"태웅": ["태웅식품", "태웅로직스", "태웅푸드"]}

STOCK_CONTEXT_WORDS = ["주가","증시","코스피","코스닥","상장","공시","실적","영업이익","매출","수급","기관","외국인","목표가","투자의견","급등","급락","상승","하락","거래량","시총","배당","분기","반기","사업보고서"]
IMPORTANT_NEWS_WORDS = [
    "실적","영업이익","매출","흑자","적자","수주","계약","공급","공시","유상증자","무상증자",
    "자사주","배당","대주주","최대주주","합병","분할","상장","투자","인수","매각","증설",
    "가이던스","목표가","리포트","투자의견","수출","해외","공장","FDA","임상","승인"
]
LOW_VALUE_NEWS_WORDS = [
    "주가","마감","하락 마감","상승 마감","장중","특징주","급등","급락","강세","약세",
    "코스피","코스닥","증시"
]
ETF_CONTEXT_WORDS = ["ETF","상장지수펀드","순자산","분배금","커버드콜","월배당","추종","지수","S&P500","나스닥","미국채","국채","채권","구성종목","리밸런싱"]

PREFERRED_PRESS = ["연합뉴스","한국경제","매일경제","서울경제","이데일리","머니투데이","조선비즈","비즈니스포스트","더벨","전자신문","ZDNet","블로터","뉴스핌"]
LOW_PRIORITY_PRESS_HINTS = ["지역","투데이","시민","데일리한국","국제뉴스","핀포인트뉴스","와이드경제","전국매일","농업경제"]

DOMAIN_PRESS_MAP = {
    "yna.co.kr": "연합뉴스",
    "hankyung.com": "한국경제",
    "mk.co.kr": "매일경제",
    "sedaily.com": "서울경제",
    "edaily.co.kr": "이데일리",
    "mt.co.kr": "머니투데이",
    "chosunbiz.com": "조선비즈",
    "businesspost.co.kr": "비즈니스포스트",
    "thebell.co.kr": "더벨",
    "etnews.com": "전자신문",
    "zdnet.co.kr": "ZDNet Korea",
    "bloter.net": "블로터",
    "newspim.com": "뉴스핌",
    "fnnews.com": "파이낸셜뉴스",
    "newsis.com": "뉴시스",
    "news1.kr": "뉴스1",
    "donga.com": "동아일보",
    "joongang.co.kr": "중앙일보",
    "chosun.com": "조선일보",
}

INDUSTRY_RULES = [
    ("반도체/IT부품", ["반도체","HBM","메모리","파운드리","디스플레이","PCB","전자부품"]),
    ("2차전지/전기차", ["2차전지","배터리","전기차","양극재","음극재","리튬"]),
    ("바이오/헬스케어", ["바이오","제약","신약","의료","헬스케어","임상"]),
    ("방산/우주항공", ["방산","무기","항공","우주","위성","드론"]),
    ("조선/기계", ["조선","선박","기계","플랜트","중공업"]),
    ("자동차/부품", ["자동차","모빌리티","타이어","현대차","기아","부품"]),
    ("AI/소프트웨어", ["AI","인공지능","소프트웨어","클라우드","데이터센터","보안"]),
    ("금융/지주", ["은행","금융","보험","증권","지주","창투","벤처"]),
    ("통신/미디어/콘텐츠", ["통신","플랫폼","콘텐츠","게임","미디어","방송"]),
    ("철강/소재/화학", ["철강","화학","소재","정유","석유","에너지"]),
    ("소비재/유통", ["유통","식품","화장품","의류","소비재"]),
    ("건설/인프라", ["건설","인프라","부동산","시멘트"]),
]
ETF_THEME_RULES = [
    ("미국 우주항공·방산·위성 테크", ["우주","우주테크","항공","스페이스"]),
    ("미국 S&P500 대형주", ["S&P500","S＆P500","미국S&P","미국 S&P"]),
    ("미국 배당성장/다우존스", ["미국배당","다우존스","SCHD"]),
    ("2차전지 밸류체인", ["2차전지","배터리"]),
    ("AI·로봇", ["AI","로봇"]),
    ("반도체", ["반도체","전공정","후공정"]),
    ("커버드콜/인컴", ["커버드콜","월배당","배당커버드콜"]),
    ("채권/혼합", ["미국채","채권","국채","혼합"]),
    ("그룹주", ["그룹"]),
    ("배당", ["배당"]),
]

ETF_HOLDINGS_HINTS = {
    "우주": "우주항공, 위성통신, 방산·항공전자, 우주 인프라 관련 미국 기업에 분산 투자하는 컨셉입니다. 민간 우주산업·위성 네트워크·방산 예산 확대 흐름에 민감합니다.",
    "우주테크": "우주항공, 위성통신, 방산·항공전자, 우주 인프라 관련 미국 기업에 분산 투자하는 컨셉입니다. 민간 우주산업·위성 네트워크·방산 예산 확대 흐름에 민감합니다.",
    "S&P500": "애플, 마이크로소프트, 엔비디아, 아마존, 알파벳 등 미국 대형 우량주 지수에 넓게 투자하는 상품입니다.",
    "미국배당": "미국 배당성장주와 우량 배당주에 분산 투자하는 상품입니다. 주가 상승보다 배당 지속성, 금리, 방어주 흐름이 중요합니다.",
    "다우존스": "미국 배당성장주와 우량 배당주에 분산 투자하는 상품입니다. 주가 상승보다 배당 지속성, 금리, 방어주 흐름이 중요합니다.",
    "2차전지": "배터리 소재, 셀, 장비, 리튬·전기차 밸류체인에 투자하는 상품입니다. 전기차 수요와 소재 가격, 중국 경쟁 상황에 민감합니다.",
    "반도체": "메모리, 비메모리, 장비, 소재, AI 데이터센터 수요와 연결되는 반도체 밸류체인 상품입니다.",
    "커버드콜": "기초자산 상승 일부를 포기하고 옵션 프리미엄과 분배금을 추구하는 인컴형 상품입니다. 강한 상승장에서는 지수형보다 수익이 제한될 수 있습니다.",
}

COMPANY_KNOWLEDGE = {
    "대원강업": "자동차용 스프링과 시트 부품을 만드는 자동차 부품사입니다. 현대차·기아 등 완성차 생산 흐름, 차량 경량화, 전기차 부품 전환, 완성차 생산량 회복 여부와 함께 봐야 합니다.",
    "금호타이어": "국내 대표 타이어 업체로 승용차·상용차용 타이어와 글로벌 교체용 타이어 시장이 핵심입니다. 해외 판매 회복, 원재료 가격, 환율, 전기차용 타이어 확대, 대주주·재무구조 이슈가 주가 판단에 중요합니다.",
    "대창솔루션": "에너지·조선·플랜트 관련 주강품과 산업 부품을 다루는 중소형주로, 원전·에너지 설비 테마와 함께 움직이는 경우가 많습니다. 테마성 수급이 강해 실적 개선 여부와 거래량 확인이 중요합니다.",
    "태웅": "풍력·조선·플랜트 등에 쓰이는 대형 자유단조품을 생산하는 업체입니다. 풍력 투자, 조선 업황, 산업설비 투자 사이클과 연결해 보는 종목입니다.",
}

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

def etf_description(stock_name: str) -> str:
    name = stock_name or ""
    for key, desc in ETF_HOLDINGS_HINTS.items():
        if key in name:
            return desc
    return "개별 기업이 아니라 여러 자산을 묶어 투자하는 ETF입니다. 상품명만으로 단정하지 말고 운용사 페이지의 구성종목, 추종지수, 분배금 정책을 함께 확인해야 합니다."

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

def parse_pubdate(value):
    value = strip_html(value)
    if not value: return None
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(KST)
    except Exception:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"):
        try:
            dt = datetime.strptime(value[:19], fmt).replace(tzinfo=KST)
            return dt
        except Exception:
            pass
    return None

def format_pubdate(value) -> str:
    dt = parse_pubdate(value)
    return dt.strftime("%Y-%m-%d") if dt else strip_html(value)

def extract_publisher(link: str = "", originallink: str = "", raw: str = "") -> str:
    raw = strip_html(raw)
    if raw: return raw
    for url in [originallink, link]:
        try:
            host = urlparse(url).netloc.lower().replace("www.", "")
            if not host: continue
            for domain, press in DOMAIN_PRESS_MAP.items():
                if domain in host: return press
            bits = host.split(".")
            if len(bits) >= 2:
                return bits[-3] if bits[-2] in ("co","com","or","ne") and len(bits) >= 3 else bits[-2]
            return host
        except Exception:
            continue
    return ""

def news_quality_score(title: str, description: str = "", pubDate: str = "", publisher: str = "", link: str = "", originallink: str = ""):
    title = strip_html(title); desc = strip_html(description)
    text = f"{title} {desc}"
    score = 0
    reasons = []

    dt = parse_pubdate(pubDate)
    if dt:
        age_days = max(0, (datetime.now(KST) - dt).days)
        if age_days <= 3: score += 5; reasons.append("fresh_3d")
        elif age_days <= 14: score += 3; reasons.append("fresh_14d")
        elif age_days <= 45: score += 1; reasons.append("fresh_45d")
        else: score -= 6; reasons.append("old_45d_plus")

    imp = sum(1 for w in IMPORTANT_NEWS_WORDS if w in text)
    low = sum(1 for w in LOW_VALUE_NEWS_WORDS if w in title)
    score += min(imp * 2, 10)
    if imp: reasons.append(f"important:{imp}")
    if low and not imp:
        score -= min(low * 2, 6); reasons.append(f"price_only:{low}")

    pub = publisher or extract_publisher(link, originallink)
    if any(p in pub for p in PREFERRED_PRESS):
        score += 2; reasons.append("preferred_press")
    if any(h in pub for h in LOW_PRIORITY_PRESS_HINTS):
        score -= 2; reasons.append("low_priority_press")

    # Example: "5월 19일 4,840원 2.42% 하락 마감" is often stale/price-only.
    if re.search(r"\d{1,2}월\s*\d{1,2}일", title) and ("마감" in title or "%" in title) and not imp:
        score -= 5; reasons.append("dated_price_close_article")

    return score, ",".join(reasons) or "neutral"

def build_news_queries(stock_name: str, stock_code: str = "", category: str = "") -> list[str]:
    stock_name = (stock_name or "").strip()
    stock_code = (stock_code or "").strip()
    if not stock_name: return []
    if is_etf_name(stock_name):
        base = [f'"{stock_name}" ETF', f'"{stock_name}" 구성종목', f'"{stock_name}" 분배금']
    else:
        base = [f'"{stock_name}" 실적', f'"{stock_name}" 공시', f'"{stock_name}" 수주', f'"{stock_name}" 주가']
        if stock_code: base.insert(1, f'"{stock_name}" {stock_code}')
    out, seen = [], set()
    for q in base:
        if q not in seen:
            seen.add(q); out.append(q)
    return out[:4]

@dataclass
class NewsScore:
    score: int
    accepted: bool
    reason: str

def score_news_match(stock_name: str, stock_code: str, title: str, description: str, query: str = "", category: str = "", pubDate: str = "", publisher: str = "", link: str = "", originallink: str = "") -> NewsScore:
    title = strip_html(title); description = strip_html(description); query = strip_html(query)
    text = " ".join([query, title, description])
    score = 0; reasons = []

    bad = false_positive_hit(stock_name, text)
    if bad: return NewsScore(-100, False, f"excluded_false_positive:{bad}")
    if not stock_name: return NewsScore(0, False, "no_stock_name")

    if stock_name in title: score += 8; reasons.append("name_in_title")
    elif stock_name in description: score += 5; reasons.append("name_in_description")
    elif stock_name in query: score += 3; reasons.append("name_in_query")

    if stock_code and stock_code in text: score += 4; reasons.append("code_match")
    toks = tokenise_name(stock_name)
    hit = sum(1 for t in toks if t in text)
    if hit: score += hit; reasons.append(f"token_hits:{hit}")

    if is_etf_name(stock_name):
        ctx = sum(1 for w in ETF_CONTEXT_WORDS if w in text)
    else:
        ctx = sum(1 for w in STOCK_CONTEXT_WORDS if w in text)
    if ctx: score += min(ctx, 4); reasons.append(f"context:{ctx}")

    qscore, qreason = news_quality_score(title, description, pubDate, publisher, link, originallink)
    score += qscore
    reasons.append(f"quality:{qscore}:{qreason}")

    if len(stock_name) <= 3 and stock_name not in title and score < 10:
        return NewsScore(score, False, "short_name_weak_match")

    return NewsScore(score, score >= 8, ",".join(reasons))

def filter_and_rank_news(stock_name: str, stock_code: str, news_rows: list[dict], limit: int = 4) -> list[dict]:
    ranked = []
    for row in news_rows:
        title = row.get("title") or row.get("제목") or ""
        desc = row.get("description") or row.get("요약") or row.get("본문") or ""
        query = row.get("query") or row.get("검색어") or ""
        link = row.get("link") or row.get("링크") or ""
        originallink = row.get("originallink") or row.get("origin_link") or ""
        pub = row.get("pubDate") or row.get("published_at") or row.get("날짜") or ""
        publisher = row.get("publisher") or row.get("언론사") or extract_publisher(link, originallink)
        score = score_news_match(stock_name, stock_code, title, desc, query, "", pub, publisher, link, originallink)
        if score.accepted:
            enriched = dict(row)
            enriched["publisher"] = publisher
            enriched["published_at"] = format_pubdate(pub)
            enriched["news_quality_score"] = news_quality_score(title, desc, pub, publisher, link, originallink)[0]
            enriched["news_match_score"] = score.score
            enriched["news_match_reason"] = score.reason
            ranked.append(enriched)
    ranked.sort(key=lambda r: int(float(r.get("news_match_score") or 0)), reverse=True)
    return ranked[:limit]

def stock_basic_info(stock_name: str, sector: str = "", reason: str = "", price: str = "", score: str = "", entry: str = "", news_rows: list[dict] | None = None) -> str:
    news_rows = news_rows or []
    if is_etf_name(stock_name):
        return f"{stock_name}: {etf_theme(stock_name)} 컨셉의 ETF입니다. {etf_description(stock_name)}"

    if stock_name in COMPANY_KNOWLEDGE:
        base = COMPANY_KNOWLEDGE[stock_name]
    else:
        category = normalize_category(stock_name, sector, reason)
        base = f"{stock_name}: {category} 관련 종목입니다. 단순 업종명보다 실제 매출원, 주요 고객사, 수주·실적 변화, 공시 이슈를 함께 확인해야 합니다."

    if news_rows:
        n = news_rows[0]
        title = strip_html(n.get("title") or n.get("제목") or "")[:90]
        pub = n.get("published_at") or format_pubdate(n.get("pubDate") or "")
        publisher = n.get("publisher") or extract_publisher(n.get("link",""), n.get("originallink",""))
        return f"{base} 최근 확인된 관련 뉴스는 {publisher + ' · ' if publisher else ''}{pub + ' · ' if pub else ''}{title}이며, 이 이슈가 실적·수급·공시 변화로 이어지는지가 핵심입니다."
    return base
