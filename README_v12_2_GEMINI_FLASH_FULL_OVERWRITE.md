# v12.2 GEMINI FLASH FULL OVERWRITE

v12.1을 먼저 덮어쓸 필요 없이 바로 적용하는 전체 패키지입니다.

## 추가/유지 기능
- v12.0 보유종목 현재가 네이버 금융 직접 조회
- v12.0 네이버뉴스 상세 API 직접 호출
- v12.2 Gemini Flash-Lite 보유종목 AI 브리핑
- AI 실패 시 규칙 기반 fallback
- Telegram 메시지에 AI 브리핑 요약과 링크 반영
- 모바일 홈에 AI 보유 브리핑 링크 추가

## GitHub Secrets에 추가할 키

```text
GEMINI_API_KEY
```

기존 키도 유지해야 합니다.

```text
NAVER_CLIENT_ID
NAVER_CLIENT_SECRET
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

## 기본 모델

```text
gemini-2.5-flash-lite
```

workflow의 `GEMINI_MODEL` 값을 바꾸면 다른 Gemini 모델로 변경할 수 있습니다.

## 포함 파일

```text
.github/workflows/daily-report.yml
automation/scripts/fetch_realtime_holdings_prices_and_naver_news.py
automation/scripts/build_gemini_holding_ai_briefing.py
automation/scripts/force_refresh_latest.py
automation/scripts/send_telegram_report_alert.py
README_v12_2_GEMINI_FLASH_FULL_OVERWRITE.md
VERIFICATION_RESULT.txt
```

## 적용 방법

1. 압축을 풉니다.
2. `.github`, `automation` 폴더를 PC의 `stock-report` 폴더에 그대로 덮어씁니다.
3. GitHub Desktop에서 변경사항 확인
4. Summary: `apply v12.2 gemini flash briefing`
5. Commit to main
6. Push origin
7. GitHub Actions에서 Run workflow 실행

## 확인할 Actions 단계

```text
Fetch REAL holding current prices and REAL Naver news detail
Build Gemini Flash holding AI briefing
Force refresh latest and mobile pages
Send Telegram report alert
```

## 생성되는 파일

```text
docs/data/latest_holding_ai_briefing.csv
docs/data/latest_holding_issue_analysis.csv
docs/details/holding_ai_briefing.html
docs/details/holding_issues.html
```

## 확인 주소

```text
https://boxinmycat.github.io/stock-report/details/holding_ai_briefing.html
https://boxinmycat.github.io/stock-report/data/latest_holding_ai_briefing.csv
https://boxinmycat.github.io/stock-report/mobile/
```
