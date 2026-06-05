# v11.2 보유종목 심화분석 패치

이번 패치는 보유종목 분석이 너무 단순하게 보이는 문제를 보완합니다.

## 추가 기능

- `docs/v11_holdings/index.html` 생성
- `docs/data/latest_holding_deep_analysis.csv` 생성
- `docs/data/latest_holding_action_guide.csv` 생성
- 엑셀 파일에 `보유종목_심화분석`, `보유대응_가이드` 시트 추가
- 모바일/최신 페이지에 v11.2 보유종목 심화분석 링크 추가

## 입력 파일 위치

반드시 저장소 루트에 있어야 합니다.

```text
stock-report/holdings_manual_input.csv
stock-report/trade_log_manual_input.csv
```

잘못된 위치:

```text
stock-report/automation/scripts/holdings_manual_input.csv
stock-report/docs/data/holdings_manual_input.csv
```

## workflow에 추가할 단계

`.github/workflows/daily-report.yml`에서 기존 v11 대시보드 단계 뒤, `Commit generated report` 전에 아래 단계를 넣으세요.

```yaml
      - name: Build v11.2 deep holdings analysis
        run: |
          python automation/scripts/build_v11_2_deep_holding_analysis.py
```

## 구글 스프레드시트 수식

새 시트를 만들고 A1에 붙여넣으세요.

```excel
=IMPORTDATA("https://boxinmycat.github.io/stock-report/data/latest_holding_deep_analysis.csv")
```

```excel
=IMPORTDATA("https://boxinmycat.github.io/stock-report/data/latest_holding_action_guide.csv")
```

## 모바일 주소

```text
https://boxinmycat.github.io/stock-report/v11_holdings/
```

## 판단 기준

- `HOLD`: 유지/관망
- `HOLD_WATCH`: 추천후보 포함, 유지 관찰
- `HOLD_ADD_WATCH`: 추천후보+뉴스 동시 포착, 추가매수 관찰
- `TAKE_PROFIT_1`: 1차 익절 고려
- `TAKE_PROFIT_2`: 목표가/강한 수익 구간, 분할 익절 고려
- `RISK_CHECK`: 손실 구간, 추가매수보다 리스크 점검
- `STOP_WATCH`: 손절 기준 근접/이탈

이 판단은 매수·매도 지시가 아니라 리포트 기반 판단 보조입니다.
