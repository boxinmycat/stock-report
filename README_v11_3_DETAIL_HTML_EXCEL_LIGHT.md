# v11.3 상세 HTML + 엑셀 경량화 패치

이 패치는 엑셀에서 숨김 처리되거나 뒤로 밀리는 중요한 상세 데이터를 모바일 HTML에서 볼 수 있게 만듭니다.
특히 `네이버뉴스_상세`, 후보 원본, 연속추천 원본, 검증 로그처럼 엑셀에서는 무겁지만 핸드폰으로 보기 좋은 자료를 `docs/details/` 아래 별도 페이지로 만듭니다.

## 추가되는 파일

```text
automation/scripts/build_v11_3_detail_html_and_cleanup.py
workflow_snippet_v11_3.txt
README_v11_3_DETAIL_HTML_EXCEL_LIGHT.md
```

## 생성되는 HTML 주소

```text
https://boxinmycat.github.io/stock-report/details/
https://boxinmycat.github.io/stock-report/details/naver_news.html
https://boxinmycat.github.io/stock-report/details/candidate_detail.html
https://boxinmycat.github.io/stock-report/details/continuous.html
https://boxinmycat.github.io/stock-report/details/holding_action.html
https://boxinmycat.github.io/stock-report/details/risk_rules.html
https://boxinmycat.github.io/stock-report/details/diagnostics.html
https://boxinmycat.github.io/stock-report/mobile/
```

## 생성되는 CSV

```text
docs/data/latest_report_basis.csv
docs/data/latest_tpsl_strategy_guide.csv
docs/data/latest_news_detail.csv
docs/data/latest_candidate_detail.csv
docs/data/latest_continuous_detail.csv
docs/data/latest_run_log.csv
```

## 엑셀 처리 방식

삭제하지 않습니다. 아래 성격의 시트는 숨김 처리합니다.

- `네이버뉴스_상세`
- `검증결과`
- RAW / Detail 성격의 무거운 시트

대신 엑셀에는 아래 시트를 추가합니다.

- `리포트_기준정보`
- `익절손절_전략기준`
- `HTML_상세보기_안내`

## workflow 적용

`.github/workflows/daily-report.yml`에서 `Commit generated report` 바로 전에 아래 단계를 추가합니다.

```yaml
      - name: Build v11.3 detail HTML and workbook cleanup
        run: |
          python automation/scripts/build_v11_3_detail_html_and_cleanup.py
```

권장 순서:

```text
Build v11 performance and holdings decision dashboard
→ Build v11.2 deep holdings analysis
→ Build v11.3 detail HTML and workbook cleanup
→ Commit generated report
```

## 구글시트 연동 예시

```excel
=IMPORTDATA("https://boxinmycat.github.io/stock-report/data/latest_report_basis.csv")
=IMPORTDATA("https://boxinmycat.github.io/stock-report/data/latest_tpsl_strategy_guide.csv")
=IMPORTDATA("https://boxinmycat.github.io/stock-report/data/latest_news_detail.csv")
```

## 주의

저장소가 public이면 보유종목, 평균단가, 거래기록, 뉴스 상세 등이 외부에 보일 수 있습니다. 민감한 정보가 들어간다면 private repo 전환을 검토하세요.
