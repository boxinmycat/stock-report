#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ensure v11 holding deep-analysis CSV files exist for GitHub Pages/Google Sheets.
This is a safety layer: if the v11.2 script did not create
latest_holding_deep_analysis.csv or latest_holding_action_guide.csv,
this script creates them from holdings_manual_input.csv.
"""
from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path('.')
DATA_DIR = ROOT / 'docs' / 'data'
HOLDING_HTML_DIR = ROOT / 'docs' / 'v11_holdings'
DETAIL_DIR = ROOT / 'docs' / 'details'

EN_HOLDINGS = ROOT / 'holdings_manual_input.csv'
KR_HOLDINGS = ROOT / '보유종목_수동입력.csv'

DEEP_CSV = DATA_DIR / 'latest_holding_deep_analysis.csv'
ACTION_CSV = DATA_DIR / 'latest_holding_action_guide.csv'


def read_csv_safely(path: Path) -> pd.DataFrame:
    for enc in ('utf-8-sig', 'utf-8', 'cp949'):
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            continue
    return pd.read_csv(path)


def to_number(x, default=0.0):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return default
    s = str(x).replace(',', '').replace('원', '').replace('%', '').strip()
    if s == '' or s.lower() in ('nan', 'none'):
        return default
    try:
        return float(s)
    except Exception:
        return default


def clean_code(x):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return ''
    s = str(x).strip()
    if s.endswith('.0') and s.replace('.0', '').isdigit():
        s = s[:-2]
    if s.isdigit() and len(s) < 6:
        s = s.zfill(6)
    return s


def normalize_holdings(df: pd.DataFrame) -> pd.DataFrame:
    # Supports both English and Korean headers.
    colmap = {
        '상태': 'status', '종목명': 'stock_name', '종목코드': 'stock_code', '보유수량': 'quantity',
        '평균단가': 'avg_price', '매수일': 'buy_date', '전략구분': 'strategy', '목표가': 'target_price',
        '손절가': 'stop_loss', '비중메모': 'weight_note', '메모': 'memo'
    }
    df = df.rename(columns={c: colmap.get(c, c) for c in df.columns})
    required = ['status','stock_name','stock_code','quantity','avg_price','buy_date','strategy','target_price','stop_loss','weight_note','memo']
    for c in required:
        if c not in df.columns:
            df[c] = ''
    df['stock_code'] = df['stock_code'].apply(clean_code)
    df['quantity_num'] = df['quantity'].apply(to_number)
    df['avg_price_num'] = df['avg_price'].apply(to_number)
    df['target_price_num'] = df['target_price'].apply(to_number)
    df['stop_loss_num'] = df['stop_loss'].apply(to_number)
    df = df[df['stock_name'].astype(str).str.strip().ne('')].copy()
    return df


def infer_action(row):
    avg = row['avg_price_num']
    target = row['target_price_num'] or (avg * 1.08 if avg else 0)
    stop = row['stop_loss_num'] or (avg * 0.93 if avg else 0)
    # Without live price, use average price as reference and mark as PLAN/HOLD.
    ref = avg
    pnl = 0.0 if avg else ''
    if not avg:
        action = 'CHECK_INPUT'
        summary = '평균단가가 없어 손익률 계산이 어렵습니다. avg_price를 확인하세요.'
    else:
        action = 'HOLD_PLAN'
        summary = '현재가 연동 전 기준입니다. 평균단가 기준으로 익절/손절 계획을 표시합니다.'
    return ref, target, stop, pnl, action, summary


def build():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    HOLDING_HTML_DIR.mkdir(parents=True, exist_ok=True)
    DETAIL_DIR.mkdir(parents=True, exist_ok=True)

    source = EN_HOLDINGS if EN_HOLDINGS.exists() else KR_HOLDINGS if KR_HOLDINGS.exists() else None
    if source is None:
        deep = pd.DataFrame([{
            'status': 'NO_INPUT', 'message': 'holdings_manual_input.csv 파일을 저장소 루트에서 찾지 못했습니다.'
        }])
        action = pd.DataFrame([{
            'status': 'NO_INPUT', 'message': '보유종목 입력 파일이 없어 보유대응 가이드를 만들 수 없습니다.'
        }])
    else:
        holdings = normalize_holdings(read_csv_safely(source))
        rows = []
        guides = []
        for _, r in holdings.iterrows():
            ref, target, stop, pnl, action_code, summary = infer_action(r)
            qty = r['quantity_num']
            avg = r['avg_price_num']
            invest_amt = qty * avg if qty and avg else 0
            tp1 = avg * 1.08 if avg else 0
            tp2 = avg * 1.15 if avg else 0
            sl = r['stop_loss_num'] or (avg * 0.93 if avg else 0)
            rows.append({
                'source_file': str(source.name),
                'stock_name': r['stock_name'],
                'stock_code': r['stock_code'],
                'status': r['status'],
                'quantity': qty,
                'avg_price': avg,
                'invest_amount': round(invest_amt, 0),
                'reference_price': ref,
                'target_price_input': r['target_price_num'],
                'stop_loss_input': r['stop_loss_num'],
                'tp1_default_8pct': round(tp1, 0) if tp1 else '',
                'tp2_default_15pct': round(tp2, 0) if tp2 else '',
                'stop_default_7pct': round(sl, 0) if sl else '',
                'pnl_pct_by_reference': pnl,
                'decision': action_code,
                'analysis_memo': summary,
                'strategy': r.get('strategy', ''),
                'memo': r.get('memo', '')
            })
            guides.append({
                'stock_name': r['stock_name'],
                'stock_code': r['stock_code'],
                'decision': action_code,
                'entry_guide': '신규 추가매수는 리포트 추천 재등장 또는 장중 거래량 확인 후 분할 진입',
                'take_profit_1': f"{round(tp1,0):,.0f}" if tp1 else '',
                'take_profit_2': f"{round(tp2,0):,.0f}" if tp2 else '',
                'stop_loss': f"{round(sl,0):,.0f}" if sl else '',
                'holding_guide': '기본 습관형 기준: +8% 1차 익절, +15% 2차 익절, -7% 손절 관찰',
                'caution': '현재가 실시간 연동 전에는 평균단가 기준 계획표로만 사용하세요. 손절가 아래 물타기 금지.'
            })
        deep = pd.DataFrame(rows)
        action = pd.DataFrame(guides)

    deep.to_csv(DEEP_CSV, index=False, encoding='utf-8-sig')
    action.to_csv(ACTION_CSV, index=False, encoding='utf-8-sig')

    html = make_html(deep, action)
    (HOLDING_HTML_DIR / 'index.html').write_text(html, encoding='utf-8')
    (DETAIL_DIR / 'holding_action.html').write_text(html, encoding='utf-8')
    print(f'✅ ensure_holding_deep_exports 완료: {DEEP_CSV}, {ACTION_CSV}')
    print(f'rows: deep={len(deep)}, action={len(action)}')


def make_html(deep: pd.DataFrame, action: pd.DataFrame) -> str:
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    style = """
    <style>
      body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f6f7fb;color:#111;margin:0;padding:16px;}
      .wrap{max-width:1100px;margin:0 auto;}
      .card{background:#fff;border-radius:16px;padding:16px;margin:14px 0;box-shadow:0 4px 14px rgba(0,0,0,.06);}
      h1{font-size:24px;margin:8px 0 4px;} h2{font-size:18px;margin:4px 0 12px;}
      .note{color:#555;font-size:14px;line-height:1.5;}
      table{border-collapse:collapse;width:100%;font-size:13px;display:block;overflow-x:auto;white-space:nowrap;}
      th,td{border-bottom:1px solid #e6e8ef;padding:8px 10px;text-align:left;}
      th{background:#f0f3f8;font-weight:700;position:sticky;top:0;}
      .badge{display:inline-block;padding:4px 8px;border-radius:999px;background:#eef6ff;color:#075985;font-weight:700;font-size:12px;}
      a{color:#2563eb;text-decoration:none;}
    </style>
    """
    deep_html = deep.to_html(index=False, escape=False)
    action_html = action.to_html(index=False, escape=False)
    return f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>보유종목 심화분석</title>{style}</head><body><div class='wrap'>
    <h1>보유종목 심화분석</h1>
    <div class='note'>생성시각: {now} · 이 페이지는 <span class='badge'>holdings_manual_input.csv</span> 기준으로 생성됩니다.</div>
    <div class='card'><h2>보유종목 심화분석</h2>{deep_html}</div>
    <div class='card'><h2>보유대응 가이드</h2>{action_html}</div>
    <div class='card note'>상세 CSV: <a href='../data/latest_holding_deep_analysis.csv'>latest_holding_deep_analysis.csv</a> · <a href='../data/latest_holding_action_guide.csv'>latest_holding_action_guide.csv</a></div>
    </div></body></html>"""


if __name__ == '__main__':
    build()
