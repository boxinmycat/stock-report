# v11.6 latest refresh fix

## 목적

`daily-stock-report`와 `pages-build-deployment`가 성공했는데도  
`https://boxinmycat.github.io/stock-report/latest/` 시간이 바뀌지 않는 문제를 고치는 패치입니다.

## 핵심 원인

리포트는 생성됐지만 `docs/latest/index.html`이 매 실행마다 수정되지 않으면 Git이 변경사항을 감지하지 못합니다.  
그러면 Pages 배포가 끝나도 latest 페이지는 예전 파일을 계속 보여줍니다.

## 포함 파일

```text
.github/workflows/daily-report.yml
automation/scripts/force_refresh_latest.py
workflow_snippet_v11_6_latest_refresh_fix.txt
README_v11_6_LATEST_REFRESH_FIX.md
```

## 적용 방법

GitHub Desktop 기준:

1. 이 압축파일을 풉니다.
2. 압축 푼 폴더 안의 `.github`, `automation` 폴더를 PC의 `stock-report` 폴더에 덮어씁니다.
3. GitHub Desktop에서 변경사항을 확인합니다.
4. Summary에 `fix latest refresh` 입력
5. `Commit to main`
6. `Push origin`
7. GitHub Actions에서 `Run workflow` 실행

## 실행 후 확인

아래 주소를 확인합니다.

```text
https://boxinmycat.github.io/stock-report/latest/
https://boxinmycat.github.io/stock-report/mobile/
https://boxinmycat.github.io/stock-report/data/latest_publish_status.csv
```

`latest_publish_status.csv`에 최신 시간이 보이면 latest 갱신 단계가 정상 실행된 것입니다.

## workflow에서 중요한 순서

아래 순서가 되어야 합니다.

```text
Archive AM PM session report
→ Publish mobile latest pages and Google Sheets CSV
→ Force refresh latest and mobile pages
→ Commit generated report
```

## 특징

- `docs/reports/**/index.html` 중 가장 최근 파일을 `docs/latest/index.html`로 복사합니다.
- 복사할 리포트가 없으면 fallback latest 페이지를 만듭니다.
- 매 실행마다 HTML comment timestamp를 추가해서 Git이 변경사항을 감지하게 합니다.
- `docs/mobile/index.html`도 함께 갱신합니다.
- `docs/data/latest_publish_status.csv`로 갱신 상태를 확인할 수 있게 합니다.
