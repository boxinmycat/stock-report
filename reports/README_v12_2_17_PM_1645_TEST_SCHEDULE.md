# v12.2.17 PM 16:45 Test Schedule

## 목적

장마감 테스트를 더 빨리 확인하기 위해 PM 리포트 예약 시간을 16:45 KST 시작으로 변경합니다.

## 변경된 스케줄

```yaml
# 08:00 KST, Monday-Friday = 23:00 UTC, Sunday-Thursday
- cron: '0 23 * * 0-4'

# 16:45 KST, Monday-Friday = 07:45 UTC, Monday-Friday
- cron: '45 7 * * 1-5'
```

## Gemini PM Only 조건

장마감 테스트 리포트 시간이 바뀌었기 때문에 Gemini 실행 조건도 아래처럼 맞췄습니다.

```yaml
if: github.event_name == 'workflow_dispatch' || github.event.schedule == '45 7 * * 1-5'
```

정기 실행 기준으로는 16:45 KST 장마감 테스트 리포트에서만 Gemini 보유 브리핑을 새로 생성합니다.  
수동 실행은 테스트 편의를 위해 Gemini를 실행합니다.

## 적용 방법

1. 압축을 풉니다.
2. `.github`, `automation`, `.gitignore`를 PC의 `stock-report` 폴더에 그대로 덮어씁니다.
3. GitHub Desktop에서 변경사항 확인
4. zip / stock_report/reports / ipynb / 대량 xlsx가 보이면 Discard
5. Summary: `apply v12.2.17 pm 1645 test schedule`
6. Commit to main
7. Push origin
8. GitHub Actions 페이지 새로고침

## 지금 적용하면 바로 실행되나?

현재 시간이 16:45 KST 이전이고, Push가 16:45 이전에 완료되면 오늘 16:45 예약 실행이 잡힐 가능성이 있습니다.

이미 16:45 KST가 지났다면 오늘 예약 실행은 지나간 것이므로 자동으로 다시 실행되지 않고 다음 평일 16:45에 실행됩니다.  
바로 확인하려면 `Run workflow` 수동 실행을 사용하세요.
