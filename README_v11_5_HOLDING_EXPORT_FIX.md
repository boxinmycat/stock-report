# v11.5 보유종목 CSV 링크 복구 패치

## 해결하는 문제
아래 두 링크가 404/비정상으로 뜨는 문제를 해결합니다.

- docs/data/latest_holding_deep_analysis.csv
- docs/data/latest_holding_action_guide.csv

## 핵심 원인
현재 workflow가 v11.2 보유종목 심화분석/CSV 생성 단계를 실행하지 않거나, 입력 파일명이 한글 파일명으로 잡혀 있어 영어 입력 파일을 읽지 못할 수 있습니다.

## 적용 방법
1. 이 압축파일을 풉니다.
2. `.github` 폴더와 `automation` 폴더를 stock-report 로컬 폴더에 덮어씁니다.
3. GitHub Desktop에서 Commit & Push 합니다.
4. Actions > daily-stock-report > Run workflow 실행합니다.
5. 아래 URL을 확인합니다.
   - https://boxinmycat.github.io/stock-report/data/latest_holding_deep_analysis.csv
   - https://boxinmycat.github.io/stock-report/data/latest_holding_action_guide.csv
   - https://boxinmycat.github.io/stock-report/v11_holdings/

## 중요한 파일 위치
입력 파일은 저장소 루트에 있어야 합니다.

- stock-report/holdings_manual_input.csv
- stock-report/trade_log_manual_input.csv

한글 파일명은 혼동 방지를 위해 루트에서 제거하거나 backup 폴더로 옮기는 것을 권장합니다.
