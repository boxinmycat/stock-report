# v11.9 FULL OVERWRITE VERIFIED

이 패키지는 GitHub Desktop에서 그대로 덮어쓰기용입니다.

## 포함 파일

```text
.github/workflows/daily-report.yml
automation/scripts/force_refresh_latest.py
automation/scripts/ensure_holdings_news_integrity.py
automation/scripts/send_telegram_report_alert.py
README_v11_9_FULL_OVERWRITE_VERIFIED.md
VERIFICATION_RESULT.txt
```

## 반드시 들어간 workflow 문구

```text
HOLDINGS_CSV_FILE: holdings_manual_input.csv
Ensure holdings code match and Naver detail exports
Force refresh latest and mobile pages
Send Telegram report alert
```

## 적용 방법

1. 압축을 풉니다.
2. 압축 푼 폴더 안의 `.github`, `automation` 폴더를 PC의 `stock-report` 폴더에 그대로 덮어씁니다.
3. GitHub Desktop에서 변경사항 확인
4. Summary: `apply v11.9 full overwrite verified`
5. Commit to main
6. Push origin
7. Actions에서 Run workflow 실행

## 실행 로그 확인

```text
Ensure holdings code match and Naver detail exports
Force refresh latest and mobile pages
Commit generated report
Send Telegram report alert
```

## 정상 로그 예시

```text
✅ holdings code/current-price matching exports ensured
✅ naver news detail exports ensured
✅ latest refreshed from: docs/reports/...
✅ latest publish status csv written
TELEGRAM_BOT_TOKEN: OK
TELEGRAM_CHAT_ID: OK
✅ Telegram alert sent
```

## 확인 주소

```text
https://boxinmycat.github.io/stock-report/data/latest_publish_status.csv
https://boxinmycat.github.io/stock-report/data/latest_holding_deep_analysis.csv
https://boxinmycat.github.io/stock-report/data/latest_holding_action_guide.csv
https://boxinmycat.github.io/stock-report/data/latest_news_detail.csv
https://boxinmycat.github.io/stock-report/details/naver_news.html
https://boxinmycat.github.io/stock-report/v11_holdings/
https://boxinmycat.github.io/stock-report/latest/?v=11_9
```
