# v11.8 FULL OVERWRITE

이 패키지는 GitHub Desktop에서 그대로 덮어쓰기용입니다.

## 포함 파일

```text
.github/workflows/daily-report.yml
automation/scripts/force_refresh_latest.py
automation/scripts/ensure_holdings_news_integrity.py
README_v11_8_FULL_OVERWRITE.md
```

## 해결하는 문제

- latest 페이지 갱신/커밋 누락
- 보유종목 stock_code 앞자리 0 누락으로 인한 현재가 매칭 실패
- `latest_holding_deep_analysis.csv` 누락
- `latest_holding_action_guide.csv` 누락
- 네이버뉴스 상세 페이지 누락
- `latest_news_detail.csv` 누락 또는 진단 부족

## 적용 방법

GitHub Desktop 기준:

1. 압축을 풉니다.
2. 압축 푼 폴더 안의 `.github`, `automation` 폴더를 PC의 `stock-report` 폴더에 그대로 덮어씁니다.
3. GitHub Desktop에서 변경사항 확인
4. Summary: `apply v11.8 full overwrite`
5. Commit to main
6. Push origin
7. GitHub Actions에서 Run workflow 실행

## 실행 로그 확인

아래 단계가 보여야 합니다.

```text
Ensure holdings code match and Naver detail exports
Force refresh latest and mobile pages
Commit generated report
```

각 단계에서 아래 문구가 나오면 정상입니다.

```text
✅ holdings code/current-price matching exports ensured
✅ naver news detail exports ensured
✅ latest refreshed from: docs/reports/...
✅ latest publish status csv written
```

## 확인 주소

```text
https://boxinmycat.github.io/stock-report/data/latest_publish_status.csv
https://boxinmycat.github.io/stock-report/data/latest_holding_deep_analysis.csv
https://boxinmycat.github.io/stock-report/data/latest_holding_action_guide.csv
https://boxinmycat.github.io/stock-report/data/latest_news_detail.csv
https://boxinmycat.github.io/stock-report/details/naver_news.html
https://boxinmycat.github.io/stock-report/v11_holdings/
https://boxinmycat.github.io/stock-report/latest/?v=11_8
```

## 참고

`current_price_source` 값 설명:

```text
matched_by_code       종목코드로 매칭 성공
matched_by_name       종목명으로 매칭 성공
fallback_avg_price    현재가를 못 찾아 평균단가로 임시 계산
not_matched           평균단가도 없거나 매칭 실패
```
