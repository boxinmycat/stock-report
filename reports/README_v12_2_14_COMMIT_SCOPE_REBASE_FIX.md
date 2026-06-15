# v12.2.14 Commit Scope + Rebase Fix

## 해결하는 오류

이번 오류는 `Commit generated report` 단계에서 발생했습니다.

```text
! [rejected] main -> main (fetch first)
Updates were rejected because the remote contains work that you do not have locally.
```

동시에 로그상 아래 파일들이 커밋 대상에 들어갔습니다.

```text
stock_report/reports/20260610/html_report_package_20260610.zip
v9_9_automation_package_20260610.zip
stock_report/reports/...
```

즉, 문제는 두 가지입니다.

1. workflow 실행 중 원격 main에 다른 커밋이 생겨서 push가 거절됨
2. notebook이 만든 중복 산출물과 zip 패키지가 커밋 대상에 들어감

## 수정 내용

- workflow 동시 실행 충돌 방지를 위해 `cancel-in-progress: true`
- commit 전에 `git fetch` + `git pull --rebase --autostash origin main`
- push 실패 시 3회 rebase 후 재시도
- `stock_report/reports`, `stock_report/latest`, `stock_report/docs` 등 중복 산출물은 커밋 제외
- `*.zip`, `*.ipynb`, root generated xlsx는 커밋 제외
- 실제 GitHub Pages에 필요한 `docs/`만 중심으로 커밋
- `.gitignore`에 대용량/중복 산출물 패턴 추가

## 적용 방법

1. 압축을 풉니다.
2. `.github`, `automation`, `.gitignore`를 PC의 `stock-report` 폴더에 그대로 덮어씁니다.
3. GitHub Desktop에서 변경사항 확인
4. Summary: `apply v12.2.14 commit scope rebase fix`
5. Commit to main
6. Push origin
7. Actions에서 Run workflow 실행

## 적용 후 기대 동작

`Commit generated report` 단계에서 더 이상 아래 파일들이 staged 되면 안 됩니다.

```text
v9_9_automation_package_*.zip
html_report_package_*.zip
stock_report/reports/**
stock_report/latest/**
stock_report/**/*.xlsx
```

커밋 대상은 주로 아래쪽만 남아야 합니다.

```text
docs/**
automation/scripts/**
.github/workflows/daily-report.yml
.gitignore
README*.md
```
