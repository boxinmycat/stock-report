# v12.2.24 KST Time Guard + Final UI Rebuild

## 핵심 수정

1. GitHub schedule을 KST timezone 명시 방식으로 변경
2. 오래 밀린 scheduled run 차단
3. 주말 scheduled run 차단
4. 모든 AI 산출물 이후 최종 UI rebuild 추가
5. run_manifest.html 생성

## 변경된 schedule

```yaml
schedule:
  - cron: '0 8 * * 1-5'
    timezone: Asia/Seoul
  - cron: '5 16 * * 1-5'
    timezone: Asia/Seoul
```

## 지연 실행 차단 기준

```text
AM 허용: 07:30~10:00 KST
PM 허용: 15:45~18:00 KST
주말 schedule: 차단
수동 실행: 허용
```

## 확인 페이지

```text
docs/details/run_manifest.html
```

## 적용 방법

1. 압축을 풉니다.
2. `.github`, `automation`, `.gitignore`를 stock-report 폴더에 덮어씁니다.
3. GitHub Desktop에서 변경사항 확인
4. zip / stock_report/reports / ipynb / 대량 xlsx가 보이면 Discard
5. Summary: `apply v12.2.24 kst guard final ui rebuild`
6. Commit to main
7. Push origin
