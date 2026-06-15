# v12.2.12 UI + Schedule + Info Refinement

## 반영 내용

- 장전 리포트 시간을 08:30 KST 기준으로 맞추고, GitHub Actions UTC cron 기준으로 수정했습니다.
  - 08:30 KST = `30 23 * * 0-4` UTC
  - 16:05 KST = `5 7 * * 1-5` UTC
- Gemini PM Only 조건도 16:05 KST에 맞춰 `github.event.schedule == '5 7 * * 1-5'`로 수정했습니다.
- `/mobile/`을 대표 통합 홈으로 두고 `/latest/`는 `/mobile/`로 자동 이동합니다.
- 추천 TOP15와 진입 시나리오에서 익절/손절을 더 보기 좋게 표시합니다.
- ETF 기본 설명을 단순 테마명에서 더 유의미한 설명으로 보강했습니다.
- 전체 추천 명단의 긴 열 너비를 더 넓혔습니다.
- 추천후보 대시보드와 전략검증을 `legacy_candidate_dashboard_validation.html`로 통합했습니다.
- 엑셀 다운로드 센터는 최신 전체 엑셀을 기본으로, 나머지는 백업/원본 후보로 명확히 구분했습니다.

## 적용 방법

1. 압축을 풉니다.
2. `.github`, `automation` 폴더를 PC의 `stock-report` 폴더에 그대로 덮어씁니다.
3. GitHub Desktop에서 변경사항 확인
4. Summary: `apply v12.2.12 ui schedule info refinement`
5. Commit to main
6. Push origin
7. Actions에서 Run workflow 실행

## 확인 주소

```text
https://boxinmycat.github.io/stock-report/mobile/
https://boxinmycat.github.io/stock-report/latest/
https://boxinmycat.github.io/stock-report/details/legacy_top15.html
https://boxinmycat.github.io/stock-report/details/legacy_full_recommendations.html
https://boxinmycat.github.io/stock-report/details/legacy_candidate_dashboard_validation.html
https://boxinmycat.github.io/stock-report/downloads/
```
