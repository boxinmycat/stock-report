#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone, timedelta
import csv, os
KST=timezone(timedelta(hours=9))
def now(): return datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')
def infer_session(event_name,event_schedule):
    if event_schedule=='30 23 * * 0-4': return 'AM'
    if event_schedule=='5 7 * * 1-5': return 'PM'
    if event_name=='workflow_dispatch': return 'MANUAL'
    h=datetime.now(KST).hour
    return 'AM' if h<12 else 'PM' if h<18 else 'MANUAL'
def main():
    event_name=os.environ.get('GITHUB_EVENT_NAME','')
    event_schedule=os.environ.get('GITHUB_EVENT_SCHEDULE','')
    rows=[
        {'key':'checked_at','value':now()},
        {'key':'event_name','value':event_name},
        {'key':'event_schedule','value':event_schedule},
        {'key':'inferred_session','value':infer_session(event_name,event_schedule)},
        {'key':'expected_am_kst','value':'08:30 KST, Monday-Friday'},
        {'key':'expected_pm_kst','value':'16:05 KST, Monday-Friday'},
        {'key':'am_cron_utc','value':'30 23 * * 0-4'},
        {'key':'pm_cron_utc','value':'5 7 * * 1-5'},
        {'key':'gemini_pm_only','value':'true'},
        {'key':'naver_client_id_env','value':'OK' if os.environ.get('NAVER_CLIENT_ID') else 'MISSING'},
        {'key':'gemini_api_key_env','value':'OK' if os.environ.get('GEMINI_API_KEY') else 'MISSING'},
        {'key':'telegram_token_env','value':'OK' if os.environ.get('TELEGRAM_BOT_TOKEN') else 'MISSING'},
        {'key':'telegram_chat_id_env','value':'OK' if os.environ.get('TELEGRAM_CHAT_ID') else 'MISSING'},
    ]
    out=Path('docs/data/latest_workflow_diagnostics.csv'); out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['key','value']); w.writeheader(); w.writerows(rows)
    print('✅ workflow diagnostics written')
    for r in rows: print(f"{r['key']}: {r['value']}")
if __name__=='__main__': main()
