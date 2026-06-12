# v12.2.20 PM 16:05 Schedule

## 목적

장마감 리포트 예약 시간을 16:45 KST에서 16:05 KST로 변경합니다.

## 변경된 스케줄

```yaml
# 08:00 KST, Monday-Friday = 23:00 UTC, Sunday-Thursday
- cron: '0 23 * * 0-4'

# 16:05 KST, Monday-Friday = 07:05 UTC, Monday-Friday
- cron: '5 7 * * 1-5'
```

## Gemini PM Only 조건

장마감 리포트 시간이 16:05 KST로 바뀌었기 때문에 Gemini 실행 조건도 함께 맞췄습니다.

```yaml
if: github.event_name == 'workflow_dispatch' || github.event.schedule == '5 7 * * 1-5'
```

## 진단값

v12.2.19의 진단 기능은 유지됩니다.  
텔레그램 메시지와 CSV에 아래 값이 찍힙니다.

```text
실행 이벤트
실행 cron
예상 KST
실제 시작 KST
```

정상적인 장마감 예약 실행이면 다음처럼 표시되어야 합니다.

```text
실행 이벤트: schedule
실행 cron: 5 7 * * 1-5
예상 KST: 16:05 KST
```

## 적용 방법

1. 압축을 풉니다.
2. `.github`, `automation`, `.gitignore`를 PC의 `stock-report` 폴더에 그대로 덮어씁니다.
3. GitHub Desktop에서 변경사항 확인
4. zip / stock_report/reports / ipynb / 대량 xlsx가 보이면 Discard
5. Summary: `apply v12.2.20 pm 1605 schedule`
6. Commit to main
7. Push origin

## 주의

16:05 KST 전에 Push까지 완료되어야 오늘 16:05 예약 실행이 잡힐 가능성이 있습니다.  
이미 16:05가 지났다면 오늘 자동 실행은 지나간 것이므로, 바로 확인하려면 `Run workflow`를 수동 실행하세요.
