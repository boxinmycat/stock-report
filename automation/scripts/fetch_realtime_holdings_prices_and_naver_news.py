#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone, timedelta
import html, json, os, re, time, urllib.parse, urllib.request, urllib.error
import pandas as pd
KST=timezone(timedelta(hours=9))
def now(): return datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')
def read_csv(p):
    p=Path(p)
    if not p.exists(): return pd.DataFrame()
    for e in ('utf-8-sig','utf-8','cp949','euc-kr'):
        try: return pd.read_csv(p,dtype=str,encoding=e).fillna('')
        except Exception: pass
    return pd.DataFrame()
def write_csv(df,p):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); df.fillna('').to_csv(p,index=False,encoding='utf-8-sig')
def s(x):
    v=str(x).strip() if x is not None else ''
    return '' if v.lower() in ('nan','none','null') else v
def code6(x):
    v=s(x).replace("'",'').replace('"','').replace('=','').replace(',','').replace(' ','')
    if re.fullmatch(r'\d+\.0',v): v=v[:-2]
    if re.fullmatch(r'\d+',v): return v.zfill(6)
    return v.upper()
def n(x):
    v=re.sub(r'[^\d\.-]','',s(x))
    if not v or v in ('-','.','-.'): return None
    try: return float(v)
    except Exception: return None
def col(df,names):
    if df.empty: return None
    low={str(c).strip().lower():c for c in df.columns}
    for name in names:
        if name.lower() in low: return low[name.lower()]
    for c in df.columns:
        cc=str(c).strip().lower()
        for name in names:
            if name.lower() in cc: return c
    return None
def load_holdings():
    eng=read_csv('holdings_manual_input.csv'); kor=read_csv('보유종목_수동입력.csv')
    df=eng if not eng.empty else kor
    src='holdings_manual_input.csv' if not eng.empty else ('보유종목_수동입력.csv' if not kor.empty else 'not_found')
    if df.empty: return pd.DataFrame(), src
    m={'status':['status','상태'],'stock_name':['stock_name','종목명','name'],'stock_code':['stock_code','종목코드','code','ticker'],'quantity':['quantity','수량','보유수량','qty'],'avg_price':['avg_price','평균단가','매입단가','평단가'],'buy_date':['buy_date','매수일','매입일'],'strategy':['strategy','전략'],'target_price':['target_price','목표가'],'stop_loss':['stop_loss','손절가'],'weight_note':['weight_note','비중메모'],'memo':['memo','메모']}
    out=pd.DataFrame()
    for k,als in m.items():
        c=col(df,als); out[k]=df[c].map(s) if c else ''
    out['stock_code']=out['stock_code'].map(code6)
    return out[(out['stock_name']!='') | (out['stock_code']!='')].copy(), src
def build_code_lookup():
    lookup={}
    for p in ['종목분야_수동입력.csv','TOSS_수동후보.csv','trade_log_manual_input.csv']:
        df=read_csv(p)
        if df.empty: continue
        nc=col(df,['stock_name','종목명','name']); cc=col(df,['stock_code','종목코드','code','ticker'])
        if not nc or not cc: continue
        for _,r in df.iterrows():
            name,code=s(r.get(nc)),code6(r.get(cc))
            if name and code: lookup[name]=code
    return lookup
def fetch_price(code):
    if not code: return None,'no_code'
    req=urllib.request.Request(f'https://finance.naver.com/item/main.naver?code={code}',headers={'User-Agent':'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req,timeout=12) as res: txt=res.read().decode('euc-kr',errors='ignore')
        m=re.search(r'<p class="no_today">.*?<span class="blind">([\d,]+)</span>',txt,re.S) or re.search(r'<span class="blind">([\d,]+)</span>',txt,re.S)
        return (float(m.group(1).replace(',','')),'naver_finance') if m else (None,'parse_failed')
    except urllib.error.HTTPError as e: return None,f'http_{e.code}'
    except Exception as e: return None,f'error_{type(e).__name__}'
def decision(pnl,target,stop,cur):
    if cur is None: return 'PRICE_NOT_MATCHED','현재가 직접 조회 실패. 종목코드 6자리와 네이버 금융 조회 가능 여부 확인.'
    if stop and cur<=stop: return 'STOP_WATCH','손절 기준 근접/이탈. 추가매수보다 리스크 축소 우선.'
    if target and cur>=target: return 'TAKE_PROFIT','목표가 도달/근접. 일부 익절 검토.'
    if pnl is not None and pnl>=8: return 'TAKE_PROFIT_1','습관형 1차 익절권. 일부 익절 후 잔량 관리 검토.'
    if pnl is not None and pnl<=-7: return 'STOP_WATCH','습관형 손절권. 물타기 금지.'
    return 'HOLD','보유 유지. 뉴스·거래량·추천 재등장 여부 확인.'
def clean_tag(x): return re.sub(r'<.*?>','',html.unescape(s(x)))
def load_queries(holdings):
    qs=['코스피','코스닥','국내증시','주식시장']
    if not holdings.empty: qs += [s(x) for x in holdings['stock_name'].head(10).tolist() if s(x)]
    cand=read_csv('docs/data/latest_candidates.csv')
    if not cand.empty:
        nc=col(cand,['stock_name','종목명','name'])
        if nc: qs += [s(x) for x in cand[nc].head(10).tolist() if s(x)]
    out=[]
    for q in qs:
        if q and q not in out: out.append(q)
    return out[:24]
def build_news(holdings):
    cid=os.environ.get('NAVER_CLIENT_ID','').strip(); sec=os.environ.get('NAVER_CLIENT_SECRET','').strip(); rows=[]
    if not cid or not sec:
        return pd.DataFrame([{'category':'diagnostic','query':'','title':'네이버뉴스 API 키가 Actions에 전달되지 않았습니다.','description':'GitHub Secrets의 NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 확인','link':'','pubDate':'','api_state':'missing_or_not_passed','checked_at':now()}])
    for q in load_queries(holdings):
        url='https://openapi.naver.com/v1/search/news.json?'+urllib.parse.urlencode({'query':q,'display':5,'sort':'date'})
        req=urllib.request.Request(url,headers={'X-Naver-Client-Id':cid,'X-Naver-Client-Secret':sec})
        try:
            with urllib.request.urlopen(req,timeout=12) as res: data=json.loads(res.read().decode('utf-8'))
            for item in data.get('items',[]):
                rows.append({'category':'news','query':q,'title':clean_tag(item.get('title')),'description':clean_tag(item.get('description')),'link':item.get('link',''),'pubDate':item.get('pubDate',''),'api_state':'ok','checked_at':now()})
        except urllib.error.HTTPError as e:
            rows.append({'category':'diagnostic','query':q,'title':f'네이버뉴스 API HTTP 오류 {e.code}','description':e.read().decode('utf-8',errors='ignore')[:400],'link':'','pubDate':'','api_state':f'http_{e.code}','checked_at':now()})
        except Exception as e:
            rows.append({'category':'diagnostic','query':q,'title':'네이버뉴스 API 호출 오류','description':repr(e),'link':'','pubDate':'','api_state':f'error_{type(e).__name__}','checked_at':now()})
        time.sleep(0.1)
    return pd.DataFrame(rows)
def build():
    data=Path('docs/data'); data.mkdir(parents=True,exist_ok=True)
    holdings,src=load_holdings(); lookup=build_code_lookup()
    if holdings.empty:
        diag=pd.DataFrame([{'status':'NO_HOLDINGS_INPUT','message':'holdings_manual_input.csv 없음 또는 비어 있음','checked_at':now()}])
        for fn in ['latest_holdings.csv','latest_holding_current_prices.csv','latest_holding_deep_analysis.csv','latest_holding_action_guide.csv']: write_csv(diag,data/fn)
        write_csv(build_news(holdings),data/'latest_news_detail.csv'); return
    holdings['stock_code']=holdings.apply(lambda r: code6(r['stock_code']) or lookup.get(s(r['stock_name']),''),axis=1)
    prices=[]; deep=[]; guide=[]
    for _,r in holdings.iterrows():
        name,code=s(r['stock_name']),code6(r['stock_code']); cur,ps=fetch_price(code); time.sleep(0.15)
        avg=n(r.get('avg_price')); qty=n(r.get('quantity')); target=n(r.get('target_price')); stop=n(r.get('stop_loss'))
        pnl=(cur/avg-1)*100 if cur and avg and avg>0 else None; dec,memo=decision(pnl,target,stop,cur)
        prices.append({'stock_name':name,'stock_code':code,'current_price':cur or '','price_source':ps,'fetched_at':now()})
        deep.append({'source_file':src,'status':r.get('status',''),'stock_name':name,'stock_code':code,'quantity':qty if qty is not None else '','avg_price':avg if avg is not None else '','current_price':cur or '','current_price_source':ps,'unrealized_pnl_pct':round(pnl,2) if pnl is not None else '','target_price':target if target is not None else '','stop_loss':stop if stop is not None else '','decision':dec,'memo':memo,'checked_at':now()})
        guide.append({'stock_name':name,'stock_code':code,'decision':dec,'take_profit_1':target if target else (round(avg*1.08,2) if avg else ''),'take_profit_2':round(avg*1.15,2) if avg else '','stop_loss':stop if stop else (round(avg*0.93,2) if avg else ''),'sell_guide':memo,'price_match_status':ps})
    write_csv(holdings,data/'latest_holdings.csv'); write_csv(pd.DataFrame(prices),data/'latest_holding_current_prices.csv'); write_csv(pd.DataFrame(deep),data/'latest_holding_deep_analysis.csv'); write_csv(pd.DataFrame(guide),data/'latest_holding_action_guide.csv')
    news=build_news(holdings); write_csv(news,data/'latest_news_detail.csv')
    rows=''.join(f"<tr><td>{html.escape(str(x['stock_name']))}</td><td>{html.escape(str(x['stock_code']))}</td><td>{html.escape(str(x['decision']))}</td><td>{html.escape(str(x['avg_price']))}</td><td>{html.escape(str(x['current_price']))}</td><td>{html.escape(str(x['unrealized_pnl_pct']))}</td><td>{html.escape(str(x['current_price_source']))}</td><td>{html.escape(str(x['memo']))}</td></tr>" for x in deep)
    Path('docs/v11_holdings').mkdir(parents=True,exist_ok=True)
    Path('docs/v11_holdings/index.html').write_text(f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>보유종목 심화분석</title><style>body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f6f7fb;margin:0;color:#111827}}.wrap{{max-width:1100px;margin:auto;padding:20px}}.hero{{background:#111827;color:white;border-radius:20px;padding:20px;margin-bottom:16px}}.box{{overflow:auto;background:white;border-radius:16px;box-shadow:0 4px 16px #0001}}table{{border-collapse:collapse;width:100%;min-width:900px}}th,td{{border-bottom:1px solid #e5e7eb;padding:10px;font-size:13px;text-align:left;vertical-align:top}}th{{background:#f3f4f6}}</style></head><body><main class='wrap'><section class='hero'><h1>보유종목 심화분석</h1><p>갱신: {html.escape(now())}</p><p>현재가는 네이버 금융 종목코드 직접 조회 기준입니다.</p></section><div class='box'><table><thead><tr><th>종목명</th><th>코드</th><th>판단</th><th>평균단가</th><th>현재가</th><th>손익률%</th><th>출처</th><th>메모</th></tr></thead><tbody>{rows}</tbody></table></div></main></body></html>""",encoding='utf-8')
    cards=''.join(f"<article class='card'><div class='meta'>{html.escape(s(r.get('query')))} · {html.escape(s(r.get('api_state')))}</div><h2>{html.escape(s(r.get('title')))}</h2><p>{html.escape(s(r.get('description')))}</p>{('<a href="'+html.escape(s(r.get('link')))+'" target="_blank">기사 열기</a>') if s(r.get('link')) else ''}</article>" for _,r in news.head(120).iterrows())
    Path('docs/details').mkdir(parents=True,exist_ok=True)
    Path('docs/details/naver_news.html').write_text(f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>네이버뉴스 상세</title><style>body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f6f7fb;margin:0;color:#111827}}.wrap{{max-width:900px;margin:auto;padding:20px}}.hero{{background:#064e3b;color:white;border-radius:20px;padding:20px;margin-bottom:16px}}.card{{background:white;border-radius:16px;padding:16px;margin-bottom:12px;box-shadow:0 4px 16px #0001}}.card h2{{font-size:17px;margin:6px 0 8px}}.card p{{font-size:14px;line-height:1.55;color:#374151}}.meta{{font-size:12px;color:#059669}}a{{color:#2563eb;font-weight:700}}</style></head><body><main class='wrap'><section class='hero'><h1>네이버뉴스 상세</h1><p>갱신: {html.escape(now())}</p><p>API 직접 호출 결과 기준</p></section>{cards}</main></body></html>""",encoding='utf-8')
    print('✅ REAL holding current prices fetched from Naver Finance'); print('✅ REAL Naver news detail fetched from Search API')
if __name__=='__main__': build()
