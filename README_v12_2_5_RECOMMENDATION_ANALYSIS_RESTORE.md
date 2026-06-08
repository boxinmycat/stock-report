# v12.2.5 Recommendation Analysis Restore

## 목적
모바일홈과 최신 리포트에 추천 종목 분석을 다시 독립 챕터로 추가합니다.

## 추가/복구 내용
- `/mobile/`에 `추천 종목 분석` 링크 추가
- `/latest/`에 `추천 종목 분석` 섹션 추가
- `/details/recommendation_analysis.html` 신규 생성
- `docs/data/latest_recommendation_analysis.csv` 신규 생성
- 추천 후보별 관심 이유 / 뉴스 흐름 / 긍정 포인트 / 주의 포인트 / 진입 관점 / 관련 뉴스 링크 제공
- Gemini PM Only, 엑셀 다운로드 챕터 유지

## 적용 방법
1. 압축을 풉니다.
2. `.github`, `automation` 폴더를 PC의 `stock-report` 폴더에 그대로 덮어씁니다.
3. GitHub Desktop에서 변경사항 확인
4. Summary: `apply v12.2.5 recommendation analysis restore`
5. Commit to main
6. Push origin
7. Actions에서 Run workflow 실행

## 확인 주소
```text
https://boxinmycat.github.io/stock-report/mobile/
https://boxinmycat.github.io/stock-report/latest/
https://boxinmycat.github.io/stock-report/details/recommendation_analysis.html
https://boxinmycat.github.io/stock-report/data/latest_recommendation_analysis.csv
```
