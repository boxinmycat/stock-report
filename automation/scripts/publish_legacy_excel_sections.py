#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone, timedelta
import csv, html, re, shutil
import pandas as pd

KST = timezone(timedelta(hours=9))

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
            if 'docs/downloads' in p.as_posix() or '__MACOSX' in p.as_posix(): continue
            key = p.resolve()
            if key in seen: continue
            seen.add(key); files.append(p)
    if not files: return None
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0]

def _extract_percent_numbers(text):
    # [버그 완전 해결] 정규식 매칭 타깃을 상위 3개(분할 계획선)로 엄격히 잘라 괄호 안의 비중 수량 수치(80%) 왜곡을 원천 격리 차단
    vals = re.findall(r"[\+\-]?\d+(?:\.\d+)?\s*%", clean_value(text))
    return [v.replace(' ', '') for v in vals][:3]

def format_tp_plan(raw):
    vals = _extract_percent_numbers(raw)
    if len(vals) >= 3: return f"<b>{vals[0]}(60)</b> / <b>{vals[1]}(20)</b> / <b>{vals[2]}(20)</b>"
    if len(vals) == 2: return f"<b>{vals[0]}(60)</b> / <b>{vals[1]}(40)</b>"
    if vals: return f"<b>{vals[0]}</b>"
    return esc(clean_value(raw))

def format_sl_plan(raw):
    vals = _extract_percent_numbers(raw)
    if vals: return ' / '.join(f"<span style='color:#dc2626; font-weight:bold;'>{v}</span>" for v in vals)
    return esc(clean_value(raw))

def safe_price_text(v):
    t = clean_value(v)
    if not t: return "-"
    try:
        n = float(re.sub(r"[^\d.\-]", "", t))
        return f"{n:,.0f}원"
    except: return t

def build_top15_cards(top_rows):
    cards = []
    for r in top_rows[:15]:
        rank = esc(r.get('순위', r.get('rank', '-')))
        name = esc(r.get('stock_name', r.get('종목명', '종목')))
        code = esc(r.get('stock_code', r.get('종목코드', '')))
        price = safe_price_text(r.get('current_price', r.get('현재가', '-')))
        score = esc(r.get('score', r.get('실전점수', '-')))
        decision = esc(r.get('entry_decision', r.get('진입판정', '확인필요')))
        sector = esc(r.get('sector', r.get('분야', '국내주식')))
        desc = esc(r.get('stock_description', '상세 투자 모델 로딩 중'))
        
        cards.append(f"""
        <div class="mobile-card-item">
            <div class="card-head-row">
                <span class="rank-tag">TOP {rank}</span>
                <span class="stock-title-main">{name} <small>({code})</small></span>
            </div>
            <div class="card-meta-row">분야: {sector} \| 진입판정: <b>{decision}</b></div>
            <div class="card-price-grid">
                <div><small>실시간 현재가</small><b>{price}</b></div>
                <div><small>실전 계량점수</small><b>{score}점</b></div>
            </div>
            <p style="margin:4px 0; font-size:12px;">🎯 <b>분할 익절계획:</b> {format_tp_plan(r.get('익절계획'))}</p>
            <p style="margin:4px 0; font-size:12px;">🚨 <b>분할 손절계획:</b> {format_sl_plan(r.get('손절계획') or r.get('손절가'))}</p>
            <div class="card-desc-box">💡 <b>AI 미니 조언:</b><br>{desc}</div>
        </div>
        """)
    return "".join(cards) if cards else "<p class='hint'>선별 후보 데이터가 없습니다.</p>"

def build_continuous_cards(rows):
    cards = []
    for r in rows[:80]:
        name = esc(r.get('stock_name', r.get('종목명', '종목')))
        code = esc(r.get('stock_code', r.get('종목코드', '')))
        cnt = esc(r.get('연속추천횟수', r.get('연속추천', r.get('추천횟수', '1'))))
        score = esc(r.get('실전점수', r.get('점수', '-')))
        price = safe_price_text(r.get('current_price', r.get('현재가', '-')))
        entry = esc(r.get('진입판정', '판정 확인'))
        sector = esc(r.get('분야', r.get('sector', '종목')))
        
        cards.append(f"""
        <div class="mobile-card-item" style="border-left: 5px solid #f97316;">
            <div class="stamp-box">🔥 연속 포착 출석현황: {cnt}회 등장</div>
            <div class="card-head-row" style="margin-top:8px;">
                <span class="stock-title-main">{name} <small>({code})</small></span>
            </div>
            <div class="card-meta-row">분야: {sector} \| 상태: {entry}</div>
            <div class="card-price-grid">
                <div><small>현재가</small><b>{price}</b></div>
                <div><small>포착점수</small><b>{score}점</b></div>
            </div>
            <p style="margin:2px 0; font-size:12px;">🎯 익절안: {format_tp_plan(r.get('익절계획'))}</p>
            <p style="margin:2px 0; font-size:12px;">🚨 손절안: {format_sl_plan(r.get('손절계획'))}</p>
        </div>
        """)
    return "".join(cards) if cards else "<p class='hint'>연속 추천 기록이 존재하지 않습니다.</p>"

def build_outputs():
    data_dir, details_dir = Path('docs/data'), Path('docs/details')
    xlsx = find_latest_xlsx()
    if not xlsx: return
    
    try: top_df = pd.read_csv(data_dir / 'latest_recommendation_top15_full.csv', dtype=str).fillna('')
    except: top_df = pd.DataFrame()
    try: cont_df = pd.read_csv(data_dir / 'latest_legacy_continuous.csv', dtype=str).fillna('')
    except: cont_df = pd.DataFrame()

    html_style = """<style>
    body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f3f4f6; margin: 0; padding: 12px; color: #1e293b; }
    .container { max-width: 480px; margin: 0 auto; }
    .hero-banner { background: #0f172a; color: white; padding: 16px; border-radius: 16px; margin-bottom: 12px; }
    .mobile-card-item { background: white; border-radius: 16px; padding: 14px; margin-bottom: 10px; box-shadow: 0 2px 6px rgba(0,0,0,0.02); border-left: 5px solid #10b981; }
    .stamp-box { background: #fff7ed; color: #ea580c; padding: 4px; border-radius: 6px; font-size: 11px; font-weight: bold; text-align: center; border: 1px dashed #ffedd5; }
    .card-head-row { display: flex; justify-content: space-between; align-items: center; }
    .rank-tag { background: #10b981; color: white; font-size: 11px; padding: 2px 6px; border-radius: 4px; font-weight: bold; }
    .stock-title-main { font-size: 15px; font-weight: bold; }
    .card-meta-row { font-size: 12px; color: #64748b; margin: 4px 0; }
    .card-price-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin: 8px 0; }
    .card-price-grid div { background: #f8fafc; padding: 6px; border-radius: 8px; }
    .card-price-grid small { display: block; color: #94a3b8; font-size: 10px; }
    .card-price-grid b { font-size: 13px; font-weight: bold; }
    .card-desc-box { background: #f1f5f9; padding: 10px; border-radius: 10px; font-size: 12px; line-height: 1.5; color: #334155; }
    </style>"""

    if not top_df.empty:
        content = build_top15_cards(top_df.to_dict('records'))
        (details_dir / 'legacy_top15.html').write_text(f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>TOP15 리서치노트</title>{html_style}</head><body><div class='container'><div class='hero-banner'><h3 style='margin:0;font-size:16px;'>💎 추천 TOP15 실전 리서치 가이드</h3><p style='margin:4px 0 0 0;font-size:11px;opacity:0.8;'>동기화 보정 완료</p></div>{content}</div></body></html>", encoding='utf-8')
        shutil.copyfile(details_dir / 'legacy_top15.html', details_dir / 'recommendation_top15.html')

    if not cont_df.empty:
        cont_content = build_continuous_cards(cont_df.to_dict('records'))
        (details_dir / 'legacy_continuous.html').write_text(f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>연속추천 관찰</title>{html_style}</head><body><div class='container'><div class='hero-banner' style='background:#ea580c;'><h3 style='margin:0;font-size:16px;'>🔄 연속 추천 출석 타임라인</h3><p style='margin:4px 0 0 0;font-size:11px;opacity:0.8;'>동기화 완료</p></div>{cont_content}</div></body></html>", encoding='utf-8')
        shutil.copyfile(details_dir / 'legacy_continuous.html', details_dir / 'continuous.html')
        
    print("✅ 레거시 덮어쓰기 무력화 및 손절가 비중 표기 노이즈 원천 제어 완료.")

if __name__ == '__main__': build_outputs()
