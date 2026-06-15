# v12.2.15 Invalid Workflow Fix

## 해결하는 문제

GitHub Actions 화면에서 `Invalid workflow file`이 뜨고 `Run workflow` 버튼이 사라지는 문제를 수정합니다.

원인은 v12.2.14 workflow 안에서 아래 두 줄이 잘못 합쳐진 것입니다.

```yaml
- name: Commit generated report      - name: Commit generated report
- name: Send Telegram report alert      - name: Send Telegram report alert
```

위 구조는 YAML 문법상 잘못되어 GitHub가 workflow를 읽지 못합니다.

## 수정 내용

정상 구조로 복구했습니다.

```yaml
- name: Commit generated report
  run: |
    ...

- name: Send Telegram report alert
  if: always()
  run: |
    python automation/scripts/send_telegram_report_alert.py
```

그리고 아침 리포트 시작 시간을 기존 논의대로 08:00 KST로 맞췄습니다.

```yaml
- cron: '0 23 * * 0-4'
```

## 적용 방법

1. 압축을 풉니다.
2. `.github`, `automation`, `.gitignore`를 PC의 `stock-report` 폴더에 그대로 덮어씁니다.
3. GitHub Desktop에서 변경사항 확인
4. Summary: `apply v12.2.15 invalid workflow fix`
5. Commit to main
6. Push origin
7. GitHub Actions 탭 새로고침

## 적용 후 확인

GitHub 웹의 `.github/workflows/daily-report.yml`에서 아래처럼 보여야 합니다.

```yaml
- name: Commit generated report
```

```yaml
- name: Send Telegram report alert
```

그리고 Actions 화면에서 `Run workflow` 버튼이 다시 보여야 합니다.
