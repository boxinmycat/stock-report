# v11.0 추천성과 검증 + 보유종목 판단 패치

이번 패치는 기존 자동 리포트에 아래 기능을 추가합니다.

## 추가 기능

| 기능 | 내용 |
|---|---|
| 추천성과 검증 | 추천 종목을 누적 저장하고 이후 리포트에서 같은 종목이 다시 등장하면 수익률을 갱신합니다. |
| 보유종목 판단 | `holdings_manual_input.csv` 기준으로 HOLD / TAKE_PROFIT / STOP_WATCH 판단을 생성합니다. |
| 진입·익절·손절 가이드 | 추천 후보별 현재가 기준 진입 범위, 1차/2차 익절, 손절 기준을 표로 생성합니다. |
| HTML 개선 | 리포트 하단에 v11 판단 섹션을 추가합니다. |
| 모바일 개선 | `docs/v11_dashboard/index.html` 단독 페이지와 모바일 메뉴 링크를 생성합니다. |
| 스프레드시트 연동 | v11 CSV 3종을 `docs/data`에 생성합니다. |

## 적용 방법

압축을 푼 뒤 GitHub Desktop으로 저장소 폴더에 그대로 덮어씁니다.

정상 위치는 아래와 같습니다.

```text
stock-report/.github/workflows/daily-report.yml
stock-report/automation/scripts/build_v11_performance_holding_dashboard.py
stock-report/automation/scripts/publish_mobile_and_sheets.py
stock-report/docs/data/.gitkeep
stock-report/docs/v11_dashboard/.gitkeep
```

그 다음 GitHub Desktop에서:

```text
Commit to main
Push origin
```

## workflow 단계 확인

`.github/workflows/daily-report.yml` 안에서 아래 순서가 있어야 합니다.

```text
Rebuild clean HTML briefing report
Build v11 performance and holdings decision dashboard
Archive AM PM session report
Publish mobile latest pages and Google Sheets CSV
Commit generated report
```

## 생성되는 주소

```text
https://boxinmycat.github.io/stock-report/mobile/
https://boxinmycat.github.io/stock-report/latest/
https://boxinmycat.github.io/stock-report/v11_dashboard/
```

## Google Sheets 수식

v11 보유종목 판단:

```text
=IMPORTDATA("https://boxinmycat.github.io/stock-report/data/latest_holding_judgment.csv")
```

v11 진입/익절/손절 가이드:

```text
=IMPORTDATA("https://boxinmycat.github.io/stock-report/data/latest_entry_exit_guide.csv")
```

v11 추천성과 검증:

```text
=IMPORTDATA("https://boxinmycat.github.io/stock-report/data/latest_performance.csv")
```

전체 추천 추적 원본:

```text
=IMPORTDATA("https://boxinmycat.github.io/stock-report/data/recommendation_tracking.csv")
```

## 주의

- 이 기능은 투자 판단 보조용입니다.
- 성과 검증은 실시간 시세 API가 아니라, 이후 리포트에서 확인되는 최신 가격을 기준으로 갱신합니다.
- 종목이 이후 리포트에 다시 등장하지 않으면 성과 갱신이 늦어질 수 있습니다.
- 보유수량/평균단가가 public GitHub Pages에 노출될 수 있으니 저장소 공개 여부를 꼭 확인하세요.
