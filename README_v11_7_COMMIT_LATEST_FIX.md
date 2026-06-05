# v11.7 commit + latest source fix

## 왜 필요한가

로그에 아래처럼 나오면 `docs/latest/index.html`은 생성됐지만 Git에 staged 되지 않은 상태입니다.

```text
no changes added to commit
No changes to commit
Everything up-to-date
```

기존 커밋 단계의 `git add docs stock_report *.xlsx *.zip ... || true`는 `*.zip` 같은 선택 파일이 없을 때 전체 `git add`가 실패할 수 있습니다.  
그래서 변경 파일이 있어도 커밋되지 않는 문제가 생깁니다.

또한 v11.6에서는 `docs/index.html`이 실제 리포트보다 수정 시간이 늦으면 latest 원본으로 잘못 선택될 수 있었습니다.  
이번 v11.7은 `docs/reports/**/index.html`을 우선 사용하도록 고쳤습니다.

## 포함 파일

```text
automation/scripts/force_refresh_latest.py
workflow_commit_step_v11_7_replace_this.txt
README_v11_7_COMMIT_LATEST_FIX.md
```

## 적용 방법

### 1. force_refresh_latest.py 덮어쓰기

압축을 풀고 아래 파일을 덮어씁니다.

```text
stock-report/automation/scripts/force_refresh_latest.py
```

### 2. workflow 커밋 단계 교체

`.github/workflows/daily-report.yml`에서 마지막의 `Commit generated report` 단계 전체를  
`workflow_commit_step_v11_7_replace_this.txt` 안의 내용으로 교체합니다.

중요한 점:

- `Force refresh latest and mobile pages` 단계는 유지
- 그 바로 다음에 새 `Commit generated report` 단계가 와야 함

## 정상 로그

정상이라면 커밋 단계에서 아래처럼 staged 파일이 보여야 합니다.

```text
Staged files:
M       docs/latest/index.html
M       docs/mobile/index.html
A       docs/data/latest_publish_status.csv
```

그리고 커밋/푸시가 진행되어야 합니다.

## 확인 주소

실행 후 Pages 배포까지 끝나면 아래를 확인합니다.

```text
https://boxinmycat.github.io/stock-report/data/latest_publish_status.csv
https://boxinmycat.github.io/stock-report/latest/?v=latest
```
