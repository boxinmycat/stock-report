# v11.4 추천목록 자동검증 + 익절/손절 전략 시뮬레이션

이번 버전의 목적은 “내 실제 매매기록”이 아니라, 먼저 **리포트가 매일 뽑는 추천목록 전체**를 기준으로 전략을 검증하는 것입니다.

## 핵심 개념

추천목록은 매일 바뀌어도 괜찮습니다.  
각 추천을 그날의 “추천 신호”로 저장해두고, 이후 리포트가 실행될 때 관측되는 가격으로 자동 추적합니다.

```text
추천 신호 = 날짜 + AM/PM + 순위 + 종목 + 추천가 + 추천모델
```

## 자동으로 되는 것

| 항목 | 설명 |
|---|---|
| 추천 스냅샷 저장 | 매일 AM/PM 추천 후보를 `recommendation_tracking.csv`에 누적 |
| 가격 관측 업데이트 | 이후 실행 때 같은 종목의 현재 가격을 찾아 최고/최저/최근 수익률 갱신 |
| 익절/손절 전략 검증 | 안정형/습관형/추세형 3개 기준을 동시에 테스트 |
| 엑셀 반영 | `추천스냅샷_추적`, `익절손절_검증`, `추천조건_검증` 시트 추가 |
| HTML 반영 | `docs/strategy/index.html` 생성 |
| 구글시트 연동 | `docs/data/latest_strategy_*.csv` 생성 |

## 전략 기준

| 전략 | 1차 익절 | 2차 익절 | 손절 | 최대보유 |
|---|---:|---:|---:|---:|
| 안정형 | +6% | +10% | -5% | 5일 |
| 습관형 | +8% | +15% | -7% | 10일 |
| 추세형 | +10% | +20% | -10% | 20일 |

초반에는 샘플이 부족하므로 `검증중`, `샘플부족`으로 표시되는 것이 정상입니다.

## 적용 방법

GitHub Desktop 기준:

```text
1. 이 zip을 다운로드
2. 압축 풀기
3. 압축 푼 내용물을 stock-report 폴더에 덮어쓰기
4. GitHub Desktop에서 변경사항 확인
5. Summary: add v11.4 strategy validation
6. Commit to main
7. Push origin
8. Actions → daily-stock-report → Run workflow
```

## workflow에 추가할 단계

`.github/workflows/daily-report.yml`에서 `Commit generated report` 전에 아래 단계를 추가하세요.

```yaml
      - name: Build v11.4 recommendation strategy validation
        run: |
          python automation/scripts/build_v11_4_strategy_validation.py
```

권장 위치:

```text
Build v11.3 detail HTML and workbook cleanup
→ Build v11.4 recommendation strategy validation
→ Commit generated report
```

v11.2, v11.3 단계를 사용 중이라면 아래 순서가 좋습니다.

```text
Build v11 performance and holdings decision dashboard
→ Build v11.2 deep holdings analysis
→ Build v11.3 detail HTML and workbook cleanup
→ Build v11.4 recommendation strategy validation
→ Commit generated report
```

## 실행 후 확인 주소

```text
https://boxinmycat.github.io/stock-report/strategy/
```

## 구글시트 수식

| 시트 이름 | A1 수식 |
|---|---|
| v11_추천전략검증 | `=IMPORTDATA("https://boxinmycat.github.io/stock-report/data/latest_strategy_validation_summary.csv")` |
| v11_추천모델검증 | `=IMPORTDATA("https://boxinmycat.github.io/stock-report/data/latest_recommendation_model_summary.csv")` |
| v11_추천추적 | `=IMPORTDATA("https://boxinmycat.github.io/stock-report/data/latest_recommendation_tracking.csv")` |
| v11_전략검증상세 | `=IMPORTDATA("https://boxinmycat.github.io/stock-report/data/latest_strategy_validation_detail.csv")` |

## 주의

- 이 검증은 추천목록 전체 기준입니다.
- 실제 매매기록 검증은 v11.5에서 별도로 붙이는 것을 추천합니다.
- 현재 스크립트는 별도 시세 API를 직접 호출하지 않고, 현재 리포트에서 관측 가능한 가격을 기반으로 누적합니다.
- 가격이 비어 있으면 `NO_PRICE`로 표시될 수 있습니다. 이 경우 추천가/현재가 컬럼이 리포트에 잘 들어오는지 확인해야 합니다.
