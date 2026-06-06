# v12.0 REAL FETCH FULL OVERWRITE

이번 패치는 v11.9에서 남아 있던 두 문제를 직접 조회 방식으로 고칩니다.

## 핵심 변경

- 보유종목 현재가를 네이버 금융에서 종목코드로 직접 조회
- 네이버뉴스 상세를 NAVER Search News API로 직접 호출
- 텔레그램 알림 유지
- latest/mobile 갱신 유지

## 포함 파일

```text
.github/workflows/daily-report.yml
automation/scripts/fetch_realtime_holdings_prices_and_naver_news.py
automation/scripts/force_refresh_latest.py
automation/scripts/send_telegram_report_alert.py
README_v12_0_REAL_FETCH_FULL_OVERWRITE.md
VERIFICATION_RESULT.txt
```

## 적용 방법

1. 압축을 풉니다.
2. `.github`, `automation` 폴더를 PC의 `stock-report` 폴더에 그대로 덮어씁니다.
3. GitHub Desktop에서 변경사항 확인
4. Summary: `apply v12 real fetch full overwrite`
5. Commit to main
6. Push origin
7. Actions에서 Run workflow 실행

## 반드시 보여야 할 Actions 단계

```text
Fetch REAL holding current prices and REAL Naver news detail
Force refresh latest and mobile pages
Send Telegram report alert
```

## 정상 로그

```text
✅ REAL holding current prices fetched from Naver Finance
✅ REAL Naver news detail fetched from Search API
✅ latest publish status csv written
✅ Telegram alert sent
```

## 확인 주소

```text
https://boxinmycat.github.io/stock-report/data/latest_holding_current_prices.csv
https://boxinmycat.github.io/stock-report/data/latest_holding_deep_analysis.csv
https://boxinmycat.github.io/stock-report/data/latest_news_detail.csv
https://boxinmycat.github.io/stock-report/v11_holdings/
https://boxinmycat.github.io/stock-report/details/naver_news.html
```
