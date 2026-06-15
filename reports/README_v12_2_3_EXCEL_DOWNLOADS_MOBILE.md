# v12.2.3 Excel Downloads on Mobile

## 목적

모바일 페이지에서 세밀한 분석용 엑셀 파일을 바로 받을 수 있도록 다운로드 챕터를 추가합니다.

## 추가 기능

- workflow에서 생성된 최신 `.xlsx` 파일을 `docs/downloads/latest_stock_report.xlsx`로 복사
- 모바일 페이지에 `엑셀/상세파일 다운로드` 챕터 추가
- 최신 리포트 페이지에도 엑셀 다운로드 섹션 추가
- `docs/downloads/index.html` 다운로드 센터 생성
- `docs/data/latest_downloads.csv` 생성

## 포함 파일

```text
.github/workflows/daily-report.yml
automation/scripts/publish_excel_downloads.py
automation/scripts/force_refresh_latest.py
automation/scripts/build_gemini_holding_ai_briefing.py
automation/scripts/fetch_realtime_holdings_prices_and_naver_news.py
automation/scripts/send_telegram_report_alert.py
README_v12_2_3_EXCEL_DOWNLOADS_MOBILE.md
VERIFICATION_RESULT.txt
```

## 적용 방법

1. 압축을 풉니다.
2. `.github`, `automation` 폴더를 PC의 `stock-report` 폴더에 그대로 덮어씁니다.
3. GitHub Desktop에서 변경사항 확인
4. Summary: `apply v12.2.3 excel downloads mobile`
5. Commit to main
6. Push origin
7. Actions에서 Run workflow 실행

## 확인할 Actions 단계

```text
Publish Excel download files
Rebuild clean latest dashboard from current data
Send Telegram report alert
```

## 확인 주소

```text
https://boxinmycat.github.io/stock-report/mobile/
https://boxinmycat.github.io/stock-report/downloads/
https://boxinmycat.github.io/stock-report/downloads/latest_stock_report.xlsx
https://boxinmycat.github.io/stock-report/data/latest_downloads.csv
```
