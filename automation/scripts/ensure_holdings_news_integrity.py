#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone, timedelta
import html, os, re
import pandas as pd
KST=timezone(timedelta(hours=9))
def now(): return datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')
def readcsv(p):
    if not Path(p).exists(): return pd.DataFrame()
    for e in ['utf-8-sig','utf-8','cp949','euc-kr']:
        try: return pd.read_csv(p,dtype=str,encoding=e).fillna('')
        except Exception: pass
    return pd.DataFrame()
def writecsv(df,p): Path(p).parent.mkdir(parents=True,exist_ok=True); df.fillna('').to_csv(p,index=False,encoding='utf-8-sig')
def clean(x):
    s='' if x is None else str(x).strip()
    return '' if s.lower() in ['nan','none','null'] else s
def code(x):
    s=clean(x).replace('=','').replace('"','').replace("'",'').replace(',','').replace(' ','')
    if re.fullmatch(r'\d+\.0',s): s=s[:-2]
    return s.zfill(6) if re.fullmatch(r'\d+',s) else s.upper()
def num(x):
    s=re.sub(r'[^\d\.\-]','',clean(x))
    try: return float(s) if s not in ['','-','.','-.'] else None
    except Exception: return None
def col(df,names):
    mp={str(c).strip().lower():c for c in df.columns}
    for n in names:
        if n.lower() in mp: return mp[n.lower()]
    for c in df.columns:
        cc=str(c).lower()
        if any(n.lower() in cc for n in names): return c
    return None
def norm_hold(df):
    cols=['status','stock_name','stock_code','quantity','avg_price','buy_date','strategy','target_price','stop_loss','weight_note','memo']
    if df.empty: return pd.DataFrame(columns=cols)
    m={'status':['status','상태'],'stock_name':['stock_name','종목명','name'],'stock_code':['stock_code','종목코드','code','ticker'],'quantity':['quantity','수량','보유수량','qty'],'avg_price':['avg_price','평균단가','매입단가','평단가'],'buy_date':['buy_date','매수일','매입일'],'strategy':['strategy','전략'],'target_price':['target_price','목표가'],'stop_loss':['stop_loss','손절가'],'weight_note':['weight_note','비중메모'],'memo':['memo','메모']}
    out=pd.DataFrame()
    for k,v in m.items():
        c=col(df,v); out[k]=df[c].map(clean) if c else ''
    out['stock_code']=out['stock_code'].map(code); out['stock_name']=out['stock_name'].map(clean)
    return out[(out.stock_name!='') | (out.stock_code!='')][cols]
def lookups():
    byn={}; byc={}; frames=[]
    for p in Path('docs/data').glob('*.csv') if Path('docs/data').exists() else []:
        df=readcsv(p); frames.append(df) if not df.empty else None
    for x in sorted(Path('.').glob('*.xlsx'),key=lambda p:p.stat().st_mtime,reverse=True)[:5]:
        try: frames += list(pd.read_excel(x,sheet_name=None,dtype=str).values())
        except Exception: pass
    for df in frames:
        if df.empty: continue
        nc=col(df,['stock_name','종목명','name']); cc=col(df,['stock_code','종목코드','code','ticker']); pc=col(df,['current_price','현재가','기준가','추천가','종가','close','price'])
        if not pc: continue
        for _,r in df.iterrows():
            price=num(r.get(pc));
            if not price or price<=0: continue
            if cc:
                cd=code(r.get(cc)); byc.setdefault(cd,price) if cd else None
            if nc:
                nm=clean(r.get(nc)); byn.setdefault(nm,price) if nm else None
    return byc,byn
def make_holdings():
    h=norm_hold(readcsv('holdings_manual_input.csv'))
    if h.empty: h=norm_hold(readcsv('보유종목_수동입력.csv'))
    src='holdings_manual_input.csv' if Path('holdings_manual_input.csv').exists() else '보유종목_수동입력.csv'
    if h.empty:
        d=pd.DataFrame([{'status':'NO_HOLDINGS_INPUT','message':'holdings_manual_input.csv 없음 또는 비어 있음','checked_at':now()}])
        for p in ['latest_holdings.csv','latest_holding_deep_analysis.csv','latest_holding_action_guide.csv']: writecsv(d,Path('docs/data')/p)
        return
    byc,byn=lookups(); rows=[]; acts=[]
    for _,r in h.iterrows():
        nm=clean(r.stock_name); cd=code(r.stock_code); avg=num(r.avg_price); target=num(r.target_price); stop=num(r.stop_loss)
        cur=None; ps='not_matched'
        if cd and cd in byc: cur=byc[cd]; ps='matched_by_code'
        elif nm and nm in byn: cur=byn[nm]; ps='matched_by_name'
        elif avg: cur=avg; ps='fallback_avg_price'
        pnl=round((cur/avg-1)*100,2) if cur and avg else ''
        if ps=='not_matched': dec='PRICE_NOT_MATCHED'; memo='현재가 매칭 필요. 종목코드 6자리 확인.'
        elif stop and cur<=stop: dec='STOP_WATCH'; memo='손절 기준가 근접/이탈. 리스크 축소 우선.'
        elif target and cur>=target: dec='TAKE_PROFIT'; memo='목표가 도달/근접. 일부 익절 검토.'
        elif pnl!='' and pnl>=8: dec='TAKE_PROFIT_1'; memo='습관형 1차 익절권. 일부 익절 검토.'
        elif pnl!='' and pnl<=-7: dec='STOP_WATCH'; memo='습관형 손절권. 물타기 금지.'
        else: dec='HOLD'; memo='보유 유지. 뉴스/거래량/재추천 확인.'
        rows.append({'source_file':src,'stock_name':nm,'stock_code':cd,'quantity':r.quantity,'avg_price':avg or '','current_price':cur or '','current_price_source':ps,'unrealized_pnl_pct':pnl,'target_price':target or '','stop_loss':stop or '','decision':dec,'memo':memo,'checked_at':now()})
        acts.append({'stock_name':nm,'stock_code':cd,'decision':dec,'take_profit_1':target or (round(avg*1.08,2) if avg else ''),'take_profit_2':round(avg*1.15,2) if avg else '','stop_loss':stop or (round(avg*0.93,2) if avg else ''),'sell_guide':memo,'price_match_status':ps})
    writecsv(h,'docs/data/latest_holdings.csv'); writecsv(pd.DataFrame(rows),'docs/data/latest_holding_deep_analysis.csv'); writecsv(pd.DataFrame(acts),'docs/data/latest_holding_action_guide.csv')
    trs=''.join(f"<tr><td>{html.escape(str(x['stock_name']))}</td><td>{html.escape(str(x['stock_code']))}</td><td>{x['decision']}</td><td>{x['avg_price']}</td><td>{x['current_price']}</td><td>{x['unrealized_pnl_pct']}</td><td>{x['current_price_source']}</td><td>{html.escape(str(x['memo']))}</td></tr>" for x in rows)
    Path('docs/v11_holdings').mkdir(parents=True,exist_ok=True)
    Path('docs/v11_holdings/index.html').write_text(f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>보유종목 심화분석</title><style>body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f6f7fb;margin:0}}.wrap{{max-width:1100px;margin:0 auto;padding:20px}}.hero{{background:#111827;color:white;border-radius:20px;padding:20px}}table{{border-collapse:collapse;width:100%;background:white}}td,th{{border-bottom:1px solid #ddd;padding:9px;font-size:13px;text-align:left}}</style></head><body><main class="wrap"><section class="hero"><h1>v11 보유종목 심화분석</h1><p>갱신: {html.escape(now())}</p></section><table><thead><tr><th>종목</th><th>코드</th><th>판단</th><th>평단</th><th>현재가</th><th>손익률</th><th>매칭</th><th>메모</th></tr></thead><tbody>{trs}</tbody></table></main></body></html>',encoding='utf-8')
def make_news():
    p=Path('docs/data/latest_news_detail.csv'); df=readcsv(p)
    api='configured' if os.getenv('NAVER_CLIENT_ID') and os.getenv('NAVER_CLIENT_SECRET') else 'missing_or_not_passed'
    if df.empty:
        df=pd.DataFrame([{'category':'diagnostic','query':'','title':'네이버뉴스 상세 데이터가 생성되지 않았습니다.','description':'NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 설정 또는 add_naver_news_summary.py 실행 로그를 확인하세요.','link':'','pubDate':'','api_state':api,'checked_at':now()}])
    else:
        df['api_state']=api; df['checked_at']=now()
    writecsv(df,p)
    cards=''
    for _,r in df.head(200).iterrows():
        title=clean(r.get('title')) or clean(r.get('제목')) or '제목 없음'; desc=clean(r.get('description')) or clean(r.get('요약')); link=clean(r.get('link')) or clean(r.get('링크'))
        a=f'<a href="{html.escape(link)}" target="_blank">기사 열기</a>' if link else '<span>링크 없음</span>'
        cards += f'<article class="card"><h2>{html.escape(title)}</h2><p>{html.escape(desc)}</p>{a}</article>'
    Path('docs/details').mkdir(parents=True,exist_ok=True)
    Path('docs/details/naver_news.html').write_text(f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>네이버뉴스 상세</title><style>body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f6f7fb;margin:0}}.wrap{{max-width:900px;margin:auto;padding:20px}}.hero{{background:#064e3b;color:white;border-radius:20px;padding:20px}}.card{{background:white;border-radius:16px;padding:16px;margin:12px 0}}</style></head><body><main class="wrap"><section class="hero"><h1>네이버뉴스 상세</h1><p>갱신: {html.escape(now())}</p><p>API 상태: {api}</p></section>{cards}</main></body></html>',encoding='utf-8')
if __name__=='__main__':
    make_holdings(); make_news(); print('✅ holdings code/current-price matching exports ensured'); print('✅ naver news detail exports ensured')
