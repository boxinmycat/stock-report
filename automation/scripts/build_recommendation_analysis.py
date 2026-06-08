#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone, timedelta
import csv, html, re

KST = timezone(timedelta(hours=9))

def now():
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")

def read_csv(path, limit=999):
    p = Path(path)
    if not p.exists():
        return []
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            with p.open(encoding=enc, newline="") as f:
                return list(csv.DictReader(f))[:limit]
        except Exception:
            pass
    return []

def write_csv(rows, path):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        rows = [{"message": "추천종목 분석 데이터가 없습니다.", "checked_at": now()}]
    fields = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with p.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

def pick(row, names):
    if not row:
        return ""
    lower = {str(k).strip().lower(): k for k in row.keys()}
    for n in names:
        k = lower.get(n.lower())
        if k and str(row.get(k, "")).strip():
            return str(row.get(k, "")).strip()
    for k, v in row.items():
        kk = str(k).lower()
        for n in names:
            if n.lower() in kk and str(v).strip():
                return str(v).strip()
    return ""

def clean(x):
    return re.sub(r"<.*?>", "", html.unescape(str(x or "").strip()))

def load_candidates():
    paths = [
        "docs/data/latest_candidates.csv",
        "docs/data/latest_candidate_detail.csv",
        "docs/data/latest_recommendations.csv",
        "docs/data/latest_strategy_validation_detail.csv",
        "recommendation_tracking.csv",
        "TOSS_수동후보.csv",
    ]
    out, seen = [], set()
    for p in paths:
        rows = read_csv(p, 100)
        for r in rows:
            name = pick(r, ["stock_name", "종목명", "name", "candidate_name"])
            code = pick(r, ["stock_code", "종목코드", "code", "ticker"])
            if not name:
                continue
            key = (name, code)
            if key in seen:
                continue
            seen.add(key)
            rr = dict(r)
            rr["_source"] = p
            out.append(rr)
        if len(out) >= 20:
            break
    return out[:15]

def related_news(news, name, limit=4):
    if not name:
        return []
    tokens = [t for t in re.split(r"[\s/·,_-]+", name) if len(t) >= 2]
    scored = []
    for r in news:
        title = clean(pick(r, ["title", "제목"]))
        desc = clean(pick(r, ["description", "요약", "본문"]))
        query = pick(r, ["query", "검색어"])
        txt = f"{query} {title} {desc}"
        score = 0
        if query == name:
            score += 10
        if name in txt:
            score += 6
        score += sum(1 for t in tokens if t in txt)
        if score:
            scored.append((score, {"title": title or "제목 없음", "desc": desc, "link": pick(r, ["link", "링크"])}))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [x[1] for x in scored[:limit]]

POS = ["실적","수주","계약","증가","성장","배당","호조","투자","목표가","강세","매출","영업이익","반등","신사업","수출","공급"]
RISK = ["하락","적자","우려","부진","규제","소송","환율","원가","급락","약세","불확실","경쟁","과열","매도"]

def hits(text, words):
    return [w for w in words if w in text][:7]

def analysis(name, score, sector, reason, links):
    text = " ".join(n["title"] + " " + n["desc"] for n in links) + " " + reason
    pos, risk = hits(text, POS), hits(text, RISK)
    score_text = f"평가값은 {score}로 표시됩니다." if score else "평가값은 명확하지 않지만 추천 후보 목록에 포함되었습니다."
    sector_text = f"{sector} 분야/테마와 연결되어 있어 업종 수급도 함께 봐야 합니다." if sector else "분야 정보가 약해 뉴스와 전략검증을 함께 봐야 합니다."
    why = f"추천 근거는 '{reason}'입니다. 이 신호가 반복되는지 확인이 필요합니다." if reason else "추천 근거 문구가 비어 있어 재등장 여부와 전략검증 결과 확인이 필요합니다."
    if links:
        titles = " / ".join(n["title"] for n in links[:2])
        issue = f"관련 뉴스에서는 '{titles}' 흐름이 확인됩니다. 추천 후보는 매수 확정이 아니라 관심 후보이므로 뉴스가 실제 거래량과 가격 반응으로 이어지는지 확인해야 합니다."
    else:
        issue = "연결된 뉴스가 충분하지 않습니다. 이 경우 뉴스 모멘텀보다 가격 위치, 거래량, 전략검증 결과를 우선해서 봐야 합니다."
    positive = f"긍정 포인트는 {', '.join(pos)} 키워드입니다. 단, 긍정 키워드만으로 추격매수하기보다 후보가 며칠 연속 유지되는지 확인하는 편이 좋습니다." if pos else "뚜렷한 긍정 키워드는 강하지 않습니다. 급하게 접근하기보다 다음 리포트 재등장 여부를 확인하는 쪽이 좋습니다."
    risk_text = f"주의 포인트는 {', '.join(risk)} 키워드입니다. 변동성이 커질 수 있으니 진입 전 손절 기준을 먼저 정해야 합니다." if risk else "명확한 리스크 키워드는 크지 않지만, 추천 후보는 신규 진입 대상이므로 손절폭과 목표가를 미리 정해야 합니다."
    entry = "진입 관점은 분할 접근입니다. 장전 후보라면 시초가 급등 추격을 피하고, 장중 거래량과 지지 여부를 확인한 뒤 접근하는 편이 좋습니다. 장마감 후보라면 다음날 갭상승 추격을 조심해야 합니다."
    return score_text, sector_text, why, issue, positive, risk_text, entry, ", ".join(pos), ", ".join(risk)

def main():
    cands = load_candidates()
    news = read_csv("docs/data/latest_news_detail.csv", 300)
    rows, cards = [], ""
    if not cands:
        write_csv([], "docs/data/latest_recommendation_analysis.csv")
        Path("docs/details").mkdir(parents=True, exist_ok=True)
        Path("docs/details/recommendation_analysis.html").write_text("<html><body><h1>추천 종목 분석 데이터 없음</h1></body></html>", encoding="utf-8")
        print("⚠️ recommendation candidates not found")
        return
    for i, c in enumerate(cands[:12], 1):
        name = pick(c, ["stock_name","종목명","name","candidate_name"])
        code = pick(c, ["stock_code","종목코드","code","ticker"])
        score = pick(c, ["score","점수","추천점수","rank_score","total_score"])
        sector = pick(c, ["sector","분야","theme","테마","industry"])
        price = pick(c, ["current_price","현재가","price","기준가","추천가","close"])
        reason = pick(c, ["reason","추천사유","comment","memo","signal","판단","decision"])
        links = related_news(news, name)
        score_text, sector_text, why, issue, positive, risk_text, entry, pos_kw, risk_kw = analysis(name, score, sector, reason, links)
        row = {
            "rank": i, "stock_name": name, "stock_code": code, "score": score, "current_price": price,
            "sector": sector, "source_file": c.get("_source",""), "score_context": score_text,
            "sector_context": sector_text, "recommend_reason": why, "news_issue": issue,
            "positive_view": positive, "risk_view": risk_text, "entry_guide": entry,
            "positive_keywords": pos_kw, "risk_keywords": risk_kw, "checked_at": now()
        }
        news_html = ""
        for j, n in enumerate(links, 1):
            row[f"news_title_{j}"] = n["title"]; row[f"news_link_{j}"] = n["link"]; row[f"news_desc_{j}"] = n["desc"]
            a = f'<a href="{html.escape(n["link"])}" target="_blank" rel="noopener">기사 보기</a>' if n["link"] else ""
            news_html += f"<li><b>{html.escape(n['title'])}</b><br><span>{html.escape(n['desc'][:180])}</span><br>{a}</li>"
        if not news_html:
            news_html = "<li>연결된 뉴스가 충분하지 않습니다.</li>"
        rows.append(row)
        cards += f"""<article class="card"><div class="head"><h2>{i}. {html.escape(name)}</h2><span>{html.escape(score or '점수 확인')}</span></div>
<div class="meta">코드 {html.escape(code)} · 기준가/현재가 {html.escape(price)} · 분야 {html.escape(sector)} · 출처 {html.escape(c.get('_source',''))}</div>
<section><h3>추천 후보로 보는 이유</h3><p>{html.escape(score_text)} {html.escape(sector_text)} {html.escape(why)}</p></section>
<section><h3>뉴스·이슈 흐름</h3><p>{html.escape(issue)}</p></section>
<section><h3>긍정 포인트</h3><p>{html.escape(positive)}</p></section>
<section><h3>주의 포인트</h3><p>{html.escape(risk_text)}</p></section>
<section><h3>진입 관점</h3><p>{html.escape(entry)}</p></section>
<section><h3>관련 뉴스 링크</h3><ul>{news_html}</ul></section></article>"""
    write_csv(rows, "docs/data/latest_recommendation_analysis.csv")
    Path("docs/details").mkdir(parents=True, exist_ok=True)
    Path("docs/details/recommendation_analysis.html").write_text(f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>추천 종목 분석</title><style>body{{margin:0;background:#f6f7fb;color:#111827;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}.wrap{{max-width:980px;margin:auto;padding:20px}}.hero{{background:#172554;color:white;border-radius:22px;padding:22px;margin-bottom:16px}}.hero p{{color:#dbeafe;line-height:1.55}}.card{{background:white;border-radius:20px;padding:18px;margin-bottom:16px;box-shadow:0 4px 16px #0001}}.head{{display:flex;justify-content:space-between;gap:12px;align-items:center;border-bottom:1px solid #e5e7eb;padding-bottom:10px;margin-bottom:12px}}.head h2{{margin:0;font-size:20px}}.head span{{background:#dbeafe;color:#1e40af;border-radius:999px;padding:6px 10px;font-weight:700;font-size:12px}}.meta{{font-size:13px;color:#6b7280;margin-bottom:14px;line-height:1.5}}section{{margin:14px 0}}h3{{font-size:15px;margin:0 0 6px}}p,li{{font-size:14px;line-height:1.72;color:#374151}}a{{color:#2563eb;font-weight:700;text-decoration:none}}</style></head><body><main class="wrap"><section class="hero"><h1>추천 종목 분석</h1><p>갱신: {html.escape(now())}<br>추천 후보는 매수 확정이 아니라 관심 후보입니다. 뉴스 흐름, 추천 근거, 리스크, 진입 관점을 함께 확인하세요.</p></section>{cards}</main></body></html>""", encoding="utf-8")
    print("✅ recommendation analysis built")
    print(f"rows: {len(rows)}")

if __name__ == "__main__":
    main()
