# v12.2.13 Stability + Info + UI Fix

## 수정 내용

- 장전/장마감 자동 실행 진단 CSV 생성: `docs/data/latest_workflow_diagnostics.csv`
- 장전 스케줄: 08:30 KST = `30 23 * * 0-4` UTC
- 장마감 스케줄: 16:05 KST = `5 7 * * 1-5` UTC
- Gemini fallback 여부 확인용 `latest_gemini_status.csv` 추가
- 추천 TOP15 기업/ETF 설명에서 현재가·점수·진입판정 중복 제거
- ETF 설명을 주요 컨셉/대표 구성자산 중심으로 보강
- 손절 표기에서 이상한 비중 숫자가 섞이는 문제 완화
- 전체 추천 명단/대시보드 긴 열 폭 확대
- 주요 뉴스 요약에서 오래된 5월 기사 fallback 최소화

## 적용 방법

1. 압축 해제
2. `.github`, `automation` 폴더를 저장소에 덮어쓰기
3. GitHub Desktop에서 commit/push
4. Actions에서 Run workflow 실행

## 확인 주소

```text
https://boxinmycat.github.io/stock-report/mobile/
https://boxinmycat.github.io/stock-report/details/legacy_top15.html
https://boxinmycat.github.io/stock-report/details/legacy_full_recommendations.html
https://boxinmycat.github.io/stock-report/details/legacy_candidate_dashboard_validation.html
https://boxinmycat.github.io/stock-report/details/naver_news.html
https://boxinmycat.github.io/stock-report/data/latest_workflow_diagnostics.csv
```
