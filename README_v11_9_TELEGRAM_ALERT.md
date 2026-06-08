# v11.9 Telegram alert patch

## 포함 파일

```text
automation/scripts/send_telegram_report_alert.py
workflow_snippet_v11_9_telegram.txt
README_v11_9_TELEGRAM_ALERT.md
```

## 적용 방법

1. 압축을 풉니다.
2. `automation/scripts/send_telegram_report_alert.py`를 저장소 같은 위치에 넣습니다.
3. `.github/workflows/daily-report.yml`에 `workflow_snippet_v11_9_telegram.txt` 내용을 반영합니다.
4. GitHub Desktop에서 Commit to main → Push origin 합니다.
5. Actions에서 Run workflow를 실행합니다.

## GitHub Secrets 필요

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

## 정상 로그

```text
Send Telegram report alert
TELEGRAM_BOT_TOKEN: OK
TELEGRAM_CHAT_ID: OK
✅ Telegram alert sent
```

## 알림 내용

- 장전/장마감/수동 리포트 구분
- 생성시각
- 추천후보 TOP
- 보유종목 판단 요약
- 전략검증 요약
- 모바일/최신/보유/전략검증 링크
