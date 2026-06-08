# v12.2.2 Restore Recommendation Interface + Gemini 3.5

## 목적

v12.2.1에서 latest/mobile이 보유종목·뉴스 중심으로 정리되면서, 기존 추천종목 분석 인터페이스가 빠져 보이는 문제를 수정합니다.

## 수정 내용

- `/latest/`에 추천 종목·관심 후보 섹션 복구
- `/latest/`에 추천전략 검증 섹션 복구
- `/mobile/`에 추천후보 상세, 연속추천/관찰, 전략검증 링크 복구
- 보유종목 현재가 섹션은 v11_holdings와 같은 최신 CSV 기준 유지
- Gemini 기본 모델을 `gemini-3.5-flash`로 설정
- Gemini 3.5 호출 실패 시 `gemini-2.5-flash` → `gemini-2.5-flash-lite` 순서로 fallback
- 텔레그램 메시지에도 추천후보 상세/전략검증 링크 유지

## 포함 파일

```text
.github/workflows/daily-report.yml
automation/scripts/fetch_realtime_holdings_prices_and_naver_news.py
automation/scripts/build_gemini_holding_ai_briefing.py
automation/scripts/force_refresh_latest.py
automation/scripts/send_telegram_report_alert.py
README_v12_2_2_RESTORE_RECOMMEND_GEMINI35.md
VERIFICATION_RESULT.txt
```

## 적용 방법

1. 압축을 풉니다.
2. `.github`, `automation` 폴더를 PC의 `stock-report` 폴더에 그대로 덮어씁니다.
3. GitHub Desktop에서 변경사항 확인
4. Summary: `apply v12.2.2 restore recommend gemini35`
5. Commit to main
6. Push origin
7. Actions에서 Run workflow 실행

## 확인할 Actions 단계

```text
Fetch REAL holding current prices and REAL Naver news detail
Build Gemini 3.5 Flash holding AI briefing
Rebuild clean latest dashboard from current data
Send Telegram report alert
```

## 확인 주소

```text
https://boxinmycat.github.io/stock-report/latest/
https://boxinmycat.github.io/stock-report/mobile/
https://boxinmycat.github.io/stock-report/details/candidate_detail.html
https://boxinmycat.github.io/stock-report/strategy/
https://boxinmycat.github.io/stock-report/v11_holdings/
https://boxinmycat.github.io/stock-report/details/holding_ai_briefing.html
```
