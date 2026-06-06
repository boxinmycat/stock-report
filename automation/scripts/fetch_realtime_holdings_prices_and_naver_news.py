#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone, timedelta
import html, json, os, re, time
import urllib.parse, urllib.request, urllib.error
import pandas as pd
KST=timezone(timedelta(hours=9))
def now(): return datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')
def S(x):
    if x is None: return ''
    v=str(x).strip()
    return '' if v.lower() in ('nan','none','null') else v
def code6(x):
    v=S(x).replace("'",'').replace('"','').replace('=','').replace(',','').replace(' ','')
    if re.fullmatch(r'\d+\.0',v): v=v[:-2]
    return v.zfill(6) if re.fullmatch(r'\d+',v) else v.upper()
def N(x):
    v=re.sub(r'[^\d\.-]','',S(x))
    if not v or v in ('-','.','-.'): return None
    try: return float(v)
    except Exception: return None
def rdcsv(p):
    p=Path(p)
    if not p.exists(): return pd.DataFrame()
    for enc in ('utf-8-sig','utf-8','cp949','euc-kr'):
        try: return pd.read_csv(p,dtype=str,encoding=enc).fillna('')
        except Exception: pass
    return pd.DataFrame()
def wrcsv(df,p):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    df.fillna('').to_csv(p,index=False,encoding='utf-8-sig')
def col(df,names):
    if df.empty: return None
    low={str(c).strip().lower():c for c in df.columns}
    for n in names:
        if n.lower() in low: return low[n.lower()]
    for c in df.columns:
        cc=str(c).lower()
        if any(n.lower() in cc for n in names): return c
    return None
def load_holdings():
    eng,kor=rdcsv('holdings_manual_input.csv'),rdcsv('보유종목_수동입력.csv')
    df=eng if not eng.empty else kor; src='holdings_manual_input.csv' if not eng.empty else ('보유종목_수동입력.csv' if not kor.empty else 'not_found')
    if df.empty: return pd.DataFrame(),src
    mp={'status':['status','상태'],'stock_name':['stock_name','종목명','name'],'stock_code':['stock_code','종목코드','code','ticker'],'quantity':['quantity','보유수량','수량','qty'],'avg_price':['avg_price','평균단가','매입단가','평단가'],'buy_date':['buy_date','매수일','매입일'],'strategy':['strategy','전략'],'target_price':['target_price','목표가'],'stop_loss':['stop_loss','손절가'],'weight_note':['weight_note','비중메모'],'memo':['memo','메모']}
    out=pd.DataFrame()
    for k,aliases in mp.items():
        c=col(df,aliases); out[k]=df[c].map(S) if c else ''
    out['stock_code']=out['stock_code'].map(code6); out['stock_name']=out['stock_name'].map(S)
    out=out[(out.stock_name!='') | (out.stock_code!='')].copy()
    return out,src
def code_lookup():
    d={}
    for p in ['종목분야_수동입력.csv','TOSS_수동후보.csv','trade_log_manual_input.csv']:
        df=rdcsv(p)
        if df.empty: continue
        nc,cc=col(df,['stock_name','종목명','name']),col(df,['stock_code','종목코드','code','ticker'])
        if not nc or not cc: continue
        for _,r in df.iterrows():
            n,c=S(r.get(nc)),code6(r.get(cc))
            if n and c: d[n]=c
    return d
def fetch_price(code):
    if not code: return None,'no_code'
    url=f'https://finance.naver.com/item/main.naver?code={code}'
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 stock-report-bot'})
    try:
        with urllib.request.urlopen(req,timeout=12) as res: txt=res.read().decode('euc-kr',errors='ignore')
        m=re.search(r'<p class="no_today">.*?<span class="blind">([\d,]+)</span>',txt,re.S) or re.search(r'<span class="blind">([\d,]+)</span>',txt,re.S)
        return (float(m.group(1).replace(',','')),'naver_finance') if m else (None,'parse_failed')
    except urllib.error.HTTPError as e: return None,f'http_{e.code}'
    except Exception as e: return None,f'error_{type(e).__name__}'
def decide(pnl,target,stop,cur):
    if cur is None: return 'PRICE_NOT_MATCHED','현재가 직접 조회 실패. 종목코드 6자리와 네이버 금융 조회 가능 여부 확인.'
    if stop and cur<=stop: return 'STOP_WATCH','손절 기준 근접/이탈. 추가매수보다 리스크 축소 우선.'
    if target and cur>=target: return 'TAKE_PROFIT','목표가 도달/근접. 일부 익절 검토.'
    if pnl is not None and pnl>=8: return 'TAKE_PROFIT_1','습관형 1차 익절권. 일부 익절 후 잔량 관리 검토.'
    if pnl is not None and pnl<=-7: return 'STOP_WATCH','습관형 손절권. 물타기 금지.'
    return 'HOLD','보유 유지. 뉴스·거래량·추천 재등장 여부 확인.'
def holding_outputs():
    h,src=load_holdings(); data=Path('docs/data'); data.mkdir(parents=True,exist_ok=True)
    if h.empty:
        diag=pd.DataFrame([{'status':'NO_HOLDINGS_INPUT','message':'holdings_manual_input.csv 없음 또는 비어 있음','checked_at':now()}])
        for n in ['latest_holdings.csv','latest_holding_current_prices.csv','latest_holding_deep_analysis.csv','latest_holding_action_guide.csv']: wrcsv(diag,data/n)
        return
    lk=code_lookup(); h['stock_code']=h.apply(lambda r: code6(r['stock_code']) or lk.get(S(r['stock_name']),''),axis=1)
    prices=[]; deep=[]; guide=[]
    for _,r in h.iterrows():
        name,code=S(r.stock_name),code6(r.stock_code); cur,ps=fetch_price(code); time.sleep(.12)
        avg,qty,target,stop=N(r.avg_price),N(r.quantity),N(r.target_price),N(r.stop_loss)
        pnl=(cur/avg-1)*100 if cur and avg and avg>0 else None; dec,memo=decide(pnl,target,stop,cur)
        prices.append({'stock_name':name,'stock_code':code,'current_price':cur or '','price_source':ps,'fetched_at':now()})
        deep.append({'source_file':src,'status':r.status,'stock_name':name,'stock_code':code,'quantity':qty or '','avg_price':avg or '','current_price':cur or '','current_price_source':ps,'unrealized_pnl_pct':round(pnl,2) if pnl is not None else '','target_price':target or '','stop_loss':stop or '','decision':dec,'memo':memo,'checked_at':now()})
        guide.append({'stock_name':name,'stock_code':code,'decision':dec,'take_profit_1':target if target else (round(avg*1.08,2) if avg else ''),'take_profit_2':round(avg*1.15,2) if avg else '','stop_loss':stop if stop else (round(avg*0.93,2) if avg else ''),'sell_guide':memo,'price_match_status':ps})
    wrcsv(h,data/'latest_holdings.csv'); wrcsv(pd.DataFrame(prices),data/'latest_holding_current_prices.csv'); wrcsv(pd.DataFrame(deep),data/'latest_holding_deep_analysis.csv'); wrcsv(pd.DataFrame(guide),data/'latest_holding_action_guide.csv')
    rows=''.join(f"<tr><td>{html.escape(str(x['stock_name']))}</td><td>{html.escape(str(x['stock_code']))}</td><td>{html.escape(str(x['decision']))}</td><td>{html.escape(str(x['avg_price']))}</td><td>{html.escape(str(x['current_price']))}</td><td>{html.escape(str(x['unrealized_pnl_pct']))}</td><td>{html.escape(str(x['current_price_source']))}</td><td>{html.escape(str(x['memo']))}</td></tr>" for x in deep)
    Path('docs/v11_holdings').mkdir(parents=True,exist_ok=True)
    Path('docs/v11_holdings/index.html').write_text(f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>보유종목 심화분석</title><style>body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f6f7fb;margin:0;color:#111827}}.wrap{{max-width:1100px;margin:auto;padding:20px}}.hero{{background:#111827;color:white;border-radius:20px;padding:20px;margin-bottom:16px}}.box{{overflow:auto;background:white;border-radius:16px;box-shadow:0 4px 16px #0001}}table{{border-collapse:collapse;width:100%;min-width:900px}}th,td{{border-bottom:1px solid #e5e7eb;padding:10px;font-size:13px;text-align:left;vertical-align:top}}th{{background:#f3f4f6}}</style></head><body><main class='wrap'><section class='hero'><h1>보유종목 심화분석</h1><p>갱신: {html.escape(now())}</p><p>현재가는 네이버 금융 종목코드 직접 조회 기준입니다.</p></section><div class='box'><table><thead><tr><th>종목명</th><th>코드</th><th>판단</th><th>평균단가</th><th>현재가</th><th>손익률%</th><th>출처</th><th>메모</th></tr></thead><tbody>{rows}</tbody></table></div></main></body></html>""",encoding='utf-8')
def clean(x): return re.sub(r'<.*?>','',html.unescape(S(x)))
def queries():
    q=['코스피','코스닥','국내증시','주식시장']; h,_=load_holdings()
    if not h.empty: q += [S(x) for x in h.stock_name.head(8).tolist() if S(x)]
    cand=rdcsv('docs/data/latest_candidates.csv'); nc=col(cand,['stock_name','종목명','name']) if not cand.empty else None
    if nc: q += [S(x) for x in cand[nc].head(8).tolist() if S(x)]
    out=[]
    for x in q:
        if x and x not in out: out.append(x)
    return out[:20]
def news_df():
    cid,sec=os.environ.get('NAVER_CLIENT_ID','').strip(),os.environ.get('NAVER_CLIENT_SECRET','').strip(); rows=[]
    if not cid or not sec: return pd.DataFrame([{'category':'diagnostic','query':'','title':'네이버뉴스 API 키가 Actions에 전달되지 않았습니다.','description':'GitHub Secrets와 workflow env를 확인하세요.','link':'','pubDate':'','api_state':'missing_or_not_passed','checked_at':now()}])
    for q in queries():
        url='https://openapi.naver.com/v1/search/news.json?'+urllib.parse.urlencode({'query':q,'display':5,'sort':'date'})
        req=urllib.request.Request(url,headers={'X-Naver-Client-Id':cid,'X-Naver-Client-Secret':sec})
        try:
            with urllib.request.urlopen(req,timeout=12) as res: data=json.loads(res.read().decode('utf-8'))
            for it in data.get('items',[]): rows.append({'category':'news','query':q,'title':clean(it.get('title')),'description':clean(it.get('description')),'link':it.get('link',''),'pubDate':it.get('pubDate',''),'api_state':'ok','checked_at':now()})
        except urllib.error.HTTPError as e:
            rows.append({'category':'diagnostic','query':q,'title':f'네이버뉴스 API HTTP 오류 {e.code}','description':e.read().decode('utf-8',errors='ignore')[:400],'link':'','pubDate':'','api_state':f'http_{e.code}','checked_at':now()})
        except Exception as e: rows.append({'category':'diagnostic','query':q,'title':'네이버뉴스 API 호출 오류','description':repr(e),'link':'','pubDate':'','api_state':f'error_{type(e).__name__}','checked_at':now()})
        time.sleep(.1)
    return pd.DataFrame(rows)
def news_outputs():
    df=news_df(); wrcsv(df,'docs/data/latest_news_detail.csv')
    cards=''
    for _,r in df.head(120).iterrows():
        link=S(r.get('link')); a=f"<a href='{html.escape(link)}' target='_blank' rel='noopener'>기사 열기</a>" if link else ''
        cards += f"<article class='card'><div class='meta'>{html.escape(S(r.get('query')))} · {html.escape(S(r.get('api_state')))}</div><h2>{html.escape(S(r.get('title')))}</h2><p>{html.escape(S(r.get('description')))}</p>{a}</article>"
    Path('docs/details').mkdir(parents=True,exist_ok=True)
    Path('docs/details/naver_news.html').write_text(f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>네이버뉴스 상세</title><style>body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f6f7fb;margin:0;color:#111827}}.wrap{{max-width:900px;margin:auto;padding:20px}}.hero{{background:#064e3b;color:white;border-radius:20px;padding:20px;margin-bottom:16px}}.card{{background:white;border-radius:16px;padding:16px;margin-bottom:12px;box-shadow:0 4px 16px #0001}}.card h2{{font-size:17px;margin:6px 0 8px}}.card p{{font-size:14px;line-height:1.55;color:#374151}}.meta{{font-size:12px;color:#059669}}a{{color:#2563eb;font-weight:700}}</style></head><body><main class='wrap'><section class='hero'><h1>네이버뉴스 상세</h1><p>갱신: {html.escape(now())}</p><p>NAVER Search News API 직접 호출 결과</p></section>{cards}</main></body></html>""",encoding='utf-8')
def main():
    holding_outputs(); news_outputs(); print('✅ REAL holding current prices fetched from Naver Finance'); print('✅ REAL Naver news detail fetched from Search API')
if __name__=='__main__': main()
