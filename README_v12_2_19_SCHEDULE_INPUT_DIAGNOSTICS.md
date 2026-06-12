# v12.2.19 Schedule Input Diagnostics

## 목적

이 버전은 잘못된 시간에 리포트가 오는 원인이 cron 입력값인지, GitHub 표시 시간대인지, 예전 workflow 실행인지 확인하기 위한 진단 패치입니다.

v12.2.18처럼 잘못된 시간 실행을 차단하는 방식이 아니라, 입력값과 실제 실행값을 기록해서 원인을 확인합니다.

## 유지되는 스케줄

```yaml
# 08:00 KST, Monday-Friday = 23:00 UTC, Sunday-Thursday
- cron: '0 23 * * 0-4'

# 16:45 KST, Monday-Friday = 07:45 UTC, Monday-Friday
- cron: '45 7 * * 1-5'
```

## 새로 추가되는 진단 단계

```yaml
- name: Diagnose schedule input values
```

이 단계가 아래 값을 로그와 CSV에 남깁니다.

```text
event_name
event_schedule
utc_started_at
kst_started_at
report_session
expected_kst
expected_kind
```

결과 파일:

```text
docs/data/latest_schedule_diagnostics.csv
```

## 텔레그램 메시지에도 추가

텔레그램 상단에 아래 값이 함께 표시됩니다.

```text
실행 이벤트
실행 cron
예상 KST
실제 시작 KST
```

이제 리포트가 이상한 시간에 오면, 텔레그램만 보고도 어떤 입력값으로 실행된 건지 확인할 수 있습니다.

## 적용 방법

1. 압축을 풉니다.
2. `.github`, `automation`, `.gitignore`를 PC의 `stock-report` 폴더에 그대로 덮어씁니다.
3. GitHub Desktop에서 변경사항 확인
4. zip / stock_report/reports / ipynb / 대량 xlsx가 보이면 Discard
5. Summary: `apply v12.2.19 schedule input diagnostics`
6. Commit to main
7. Push origin
