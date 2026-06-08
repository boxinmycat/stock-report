# v11.7 FULL OVERWRITE

이 패키지는 부분 수정 없이 덮어쓰기용입니다.

## 포함 파일

```text
.github/workflows/daily-report.yml
automation/scripts/force_refresh_latest.py
README_v11_7_FULL_OVERWRITE.md
```

## 적용 방법

GitHub Desktop 기준:

1. 압축을 풉니다.
2. 압축 푼 폴더 안의 `.github` 폴더와 `automation` 폴더를 PC의 `stock-report` 폴더에 그대로 덮어씁니다.
3. GitHub Desktop에서 변경사항 확인
4. Summary: `apply v11.7 full overwrite`
5. Commit to main
6. Push origin
7. GitHub Actions에서 Run workflow 실행

## 정상 로그

Actions 로그에서 아래 단계가 보여야 합니다.

```text
Force refresh latest and mobile pages
Commit generated report
```

`Force refresh latest and mobile pages` 단계에서:

```text
✅ latest refreshed from: docs/reports/...
✅ mobile page refreshed: docs/mobile/index.html
✅ latest publish status csv written
```

`Commit generated report` 단계에서:

```text
Staged files:
M docs/latest/index.html
M docs/mobile/index.html
A docs/data/latest_publish_status.csv
```

이렇게 나오면 정상입니다.

## 확인 주소

```text
https://boxinmycat.github.io/stock-report/data/latest_publish_status.csv
https://boxinmycat.github.io/stock-report/latest/?v=11_7
https://boxinmycat.github.io/stock-report/mobile/?v=11_7
```
