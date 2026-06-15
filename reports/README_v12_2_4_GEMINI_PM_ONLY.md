# v12.2.4 Gemini PM Only

## 목적

Gemini API 비용을 줄이기 위해 보유종목 AI 브리핑을 장마감 리포트에서만 새로 생성하도록 수정합니다.

## 운영 방식

```text
08:35 장전 리포트
- 추천후보 / 전략검증 / 보유종목 현재가 / 네이버뉴스 / 엑셀 다운로드 유지
- Gemini AI 보유 브리핑은 새로 생성하지 않음

16:05 장마감 리포트
- 추천후보 / 전략검증 / 보유종목 현재가 / 네이버뉴스 유지
- Gemini 3.5 Flash 보유종목 AI 브리핑 생성
- 텔레그램에 AI 요약 포함
```

## 포함 파일

```text
.github/workflows/daily-report.yml
automation/scripts/force_refresh_latest.py
automation/scripts/send_telegram_report_alert.py
automation/scripts/publish_excel_downloads.py
automation/scripts/build_gemini_holding_ai_briefing.py
automation/scripts/fetch_realtime_holdings_prices_and_naver_news.py
README_v12_2_4_GEMINI_PM_ONLY.md
VERIFICATION_RESULT.txt
```

## 적용 방법

1. 압축을 풉니다.
2. `.github`, `automation` 폴더를 PC의 `stock-report` 폴더에 그대로 덮어씁니다.
3. GitHub Desktop에서 변경사항 확인
4. Summary: `apply v12.2.4 gemini pm only`
5. Commit to main
6. Push origin
7. Actions에서 Run workflow 실행

## 핵심 수정

workflow의 Gemini 단계가 아래 조건으로 바뀝니다.

```yaml
if: github.event_name == 'workflow_dispatch' || github.event.schedule == '5 16 * * 1-5'
```

즉, 정기 실행 기준으로는 16:05 장마감 리포트에서만 Gemini를 호출합니다.  
수동 실행은 테스트 편의를 위해 Gemini를 호출하도록 남겨두었습니다.

## 확인할 Actions 동작

장전 예약 실행에서는 아래 단계가 skipped 처리되어야 합니다.

```text
Build Gemini 3.5 Flash holding AI briefing
```

장마감 예약 실행 또는 수동 실행에서는 실행됩니다.
