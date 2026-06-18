# -*- coding: utf-8 -*-
import os, sys, html, json, re, time, urllib.parse, urllib.request
from pathlib import Path
import pandas as pd
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
def now(): return datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')

def load_trade_logs():
    for p in [Path("docs/data/toss_trade_history.csv"), Path("trade_log_manual_input.csv"), Path("매매기록_수동입력.csv")]:
        # 🧼 [안전벨트] 파일이 존재하고, 크기가 0바이트보다 클 때만 읽도록 철저히 방어
        if p.exists() and p.stat().st_size > 0:
            try:
                df = pd.read_csv(p, dtype=str).fillna("")
                if not df.empty: return df
            except Exception:
                pass
    return pd.DataFrame()

def call_gemini_eval(prompt_content):
    key = os.environ.get('GEMINI_API_KEY','').strip()
    if not key: return "Gemini API Key 세팅을 확인하세요."
    url = f"[https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent](https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent)"
    payload = {
        'contents': [{'parts': [{'text': prompt_content}]}],
        'generationConfig': {'temperature': 0.2, 'maxOutputTokens': 1500}
    }
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json', 'x-goog-api-key': key})
        with urllib.request.urlopen(req, timeout=40) as res:
            data = json.loads(res.read().decode('utf-8'))
        return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"AI 연동 실패 사유: {repr(e)}"

def build():
    df = load_trade_logs()
    if df.empty:
        text = "<p class='hint'>추적 가능한 최근 60일 내 매매 체결 기록이 존재하지 않습니다. 토스 Open API가 연동되거나 수동 로그를 채우면 활성화됩니다.</p>"
    else:
        log_dump = ""
        for idx, row in df.head(15).iterrows():
            log_dump += f"- 날짜: {row.get('trade_date', row.get('체결일',''))} | 종목: {row.get('stock_name','')} | 구분: {row.get('trade_type', row.get('매매구분',''))} | 수량: {row.get('quantity','')} | 체결가: {row.get('price', row.get('체결가',''))}\\n"
        
        prompt = f"""
        당신은 투자자의 실전 매매 기록(Trade History)을 분석하여 날카로운 훈수를 두는 월가 출신의 인공지능 매매 복기 매니저입니다.
        아래의 최근 매매 내역 데이터 뭉치를 바탕으로 보유 기간, 실현 이익 금액의 적절성을 평가하십시오.
        
        [실전 매매 로그]
        {log_dump}
        
        [지시 및 조언 규칙]
        1. 무조건 투자자 눈높이에 맞춰 친절하면서도 뼈를 때리는 실전 조언을 건네십시오.
        2. '이 거래는 적절하게 이익을 잘 냈다' 혹은 '중간에 이때 팔고 더 떨어졌을 때 다시 기계적으로 재매수 대응을 했어야 했다'와 같이 시스템 분할 손절·익절 공식을 따르지 않아 놓친 기회비용을 명확히 분석 복기해 주십시오.
        3. 깔끔하게 줄바꿈 문장 형태로 단락을 나누어 회신해 주십시오.
        """
        text = call_gemini_eval(prompt).replace('\n', '<br>').replace('**', '')

    page = f"""<!doctype html>
    <html lang="ko">
    <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>AI 매매 복기 노트</title>
    <style>
    body {{ font-family: -apple-system, sans-serif; background: #f3f4f6; margin: 0; padding: 12px; color: #1e293b; }}
    .container {{ max-width: 480px; margin: 0 auto; }}
    .banner {{ background: #0284c7; color: white; padding: 16px; border-radius: 16px; margin-bottom: 12px; }}
    .eval-card {{ background: white; border-radius: 16px; padding: 16px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.02); border-left: 5px solid #0284c7; font-size: 13px; line-height: 1.6; color: #334155; }}
    </style>
    </head>
    <body>
    <div class="container">
        <div class="banner">
            <h3 style="margin:0; font-size: 16px;">📈 AI 실전 매매 복기·타점 평가</h3>
            <p style="margin:4px 0 0 0; font-size:11px; opacity:0.85;">동기화 시각: {now()}</p>
        </div>
        <div class="eval-card">
            {text}
        </div>
    </div>
    </body>
    </html>"""
    Path('docs/details/trade_evaluation.html').write_text(page, encoding='utf-8')

if __name__ == '__main__': build()
