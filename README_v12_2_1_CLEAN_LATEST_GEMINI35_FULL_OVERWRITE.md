# v12.2.1 CLEAN LATEST + GEMINI 3.5 FLASH FULL OVERWRITE

## 해결하는 문제

1. `/latest/`에서는 보유종목 현재가 오류가 보이는데 `/v11_holdings/`에서는 정상으로 보이는 문제
   - 원인: latest가 예전 노트북 리포트 HTML을 복사해서 보여주면서 오래된 보유종목 관리 문구가 남을 수 있음
   - 수정: latest를 기존 HTML 복사 방식이 아니라 `docs/data/latest_holding_deep_analysis.csv`와 `latest_holding_ai_briefing.csv` 기준으로 새로 생성

2. Gemini 모델 기준 정리
   - `GEMINI_MODEL: gemini-3.5-flash`로 변경
   - 호출 실패 시 `gemini-2.5-flash`, `gemini-2.5-flash-lite` 순서로 자동 fallback

## 적용 방법

1. 압축을 풉니다.
2. `.github`, `automation` 폴더를 PC의 `stock-report` 폴더에 그대로 덮어씁니다.
3. GitHub Desktop에서 변경사항 확인
4. Summary: `apply v12.2.1 clean latest gemini35`
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
https://boxinmycat.github.io/stock-report/v11_holdings/
https://boxinmycat.github.io/stock-report/details/holding_ai_briefing.html
https://boxinmycat.github.io/stock-report/data/latest_holding_deep_analysis.csv
https://boxinmycat.github.io/stock-report/data/latest_holding_ai_briefing.csv
```
