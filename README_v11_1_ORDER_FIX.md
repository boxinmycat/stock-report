# v11.1 order fix: mobile/latest + v11 dashboard + sheets formulas

이 패치는 v11.0 기능이 `latest` HTML에 덮어써져 사라지는 문제를 막기 위해 workflow 순서를 조정합니다.

정상 실행 순서:
1. 노트북 실행
2. 네이버뉴스/보유종목 반영
3. 클린 HTML 재생성
4. AM/PM 리포트 보관
5. mobile/latest 및 Google Sheets CSV 생성
6. v11 추천성과/보유판단 대시보드 생성 및 latest HTML에 삽입
7. GitHub 커밋

보유종목 파일 위치:
- stock-report/holdings_manual_input.csv
- stock-report/trade_log_manual_input.csv

수동 편집 대상은 위 2개 파일입니다. `docs/data/latest_*.csv` 파일은 자동 생성 결과물이므로 직접 수정하지 않습니다.
