# v12.2.8 Legacy Excel Data Restore

## 목적

새로 추천분석을 추정 생성하지 않고, 엑셀 리포트 안에 이미 들어 있던 v10 계열 데이터를 모바일/HTML로 다시 꺼내오도록 수정합니다.

## 핵심 변경

- 최신 `.xlsx` 파일에서 기존 시트를 직접 읽음
- `모바일_대시보드`
- `TOP후보_요약`
- `추천 리스트`
- `진입시나리오`
- `진입가이드_요약`
- `연속추천_관찰`
- `추천성과_검증`
- `전략백테스트요약`
- `계좌백테스트요약`
- `보유종목_판단`

## 생성/복원되는 페이지

```text
docs/details/legacy_top15.html
docs/details/legacy_full_recommendations.html
docs/details/legacy_entry_scenario.html
docs/details/legacy_continuous.html
docs/details/legacy_strategy_validation.html
docs/details/legacy_mobile_dashboard.html
docs/details/legacy_holding_decision.html
```

## 최신/모바일 반영

```text
docs/latest/index.html
docs/mobile/index.html
```

모바일 홈은 아래 챕터로 다시 구성됩니다.

```text
추천 종목
- 추천 TOP15
- 전체 추천 명단
- 진입 시나리오
- 연속추천 관찰
- 전략 추천/검증
- 원본 모바일 대시보드

보유 종목
- 보유종목 상세
- 보유종목 AI 브리핑
- 기존 보유종목 판단

뉴스/자료
- 네이버뉴스 상세
- 엑셀 다운로드
- 최신 리포트
```

## 적용 방법

1. 압축을 풉니다.
2. `.github`, `automation` 폴더를 PC의 `stock-report` 폴더에 그대로 덮어씁니다.
3. GitHub Desktop에서 변경사항 확인
4. Summary: `apply v12.2.8 legacy excel data restore`
5. Commit to main
6. Push origin
7. Actions에서 Run workflow 실행

## 확인할 Actions 단계

```text
Restore legacy Excel report sections
Force refresh latest and mobile pages
```

## 확인 주소

```text
https://boxinmycat.github.io/stock-report/mobile/
https://boxinmycat.github.io/stock-report/latest/
https://boxinmycat.github.io/stock-report/details/legacy_top15.html
https://boxinmycat.github.io/stock-report/details/legacy_full_recommendations.html
https://boxinmycat.github.io/stock-report/details/legacy_entry_scenario.html
https://boxinmycat.github.io/stock-report/details/legacy_continuous.html
https://boxinmycat.github.io/stock-report/details/legacy_strategy_validation.html
https://boxinmycat.github.io/stock-report/data/latest_legacy_sections_status.csv
```
