# v10.9 Mobile + Google Sheets Patch

이 패치는 휴대폰에서 리포트를 편하게 보기 위한 `latest` 페이지와, 구글 스프레드시트에서 불러올 수 있는 `latest_*.csv` 파일을 자동 생성합니다.

## 추가되는 파일

```text
.github/workflows/daily-report.yml
automation/scripts/publish_mobile_and_sheets.py
docs/data/.gitkeep
docs/latest/.gitkeep
docs/mobile/.gitkeep
```

## 생성되는 URL

```text
https://boxinmycat.github.io/stock-report/
https://boxinmycat.github.io/stock-report/latest/
https://boxinmycat.github.io/stock-report/mobile/
```

핸드폰에서는 아래 주소를 크롬/사파리에서 열고 홈 화면에 추가하면 됩니다.

```text
https://boxinmycat.github.io/stock-report/mobile/
```

## Google Sheets 수식

구글 스프레드시트에서 새 시트를 만들고 A1 셀에 아래 수식을 붙여넣습니다.

추천후보:
```text
=IMPORTDATA("https://boxinmycat.github.io/stock-report/data/latest_candidates.csv")
```

보유종목:
```text
=IMPORTDATA("https://boxinmycat.github.io/stock-report/data/latest_holdings.csv")
```

매매기록:
```text
=IMPORTDATA("https://boxinmycat.github.io/stock-report/data/latest_trade_log.csv")
```

네이버뉴스 요약:
```text
=IMPORTDATA("https://boxinmycat.github.io/stock-report/data/latest_news_summary.csv")
```

최신 리포트 정보:
```text
=IMPORTDATA("https://boxinmycat.github.io/stock-report/data/latest_report_summary.csv")
```

## 주의

- GitHub Pages 또는 CSV URL이 외부에서 접근 가능해야 Google Sheets `IMPORTDATA`가 작동합니다.
- Public 저장소라면 보유수량/평균단가가 노출될 수 있습니다.
- 민감정보가 걱정되면 보유수량/평균단가를 CSV에서 비우거나 저장소를 private으로 바꾸는 방향을 검토하세요.
