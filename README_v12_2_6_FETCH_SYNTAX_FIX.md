# v12.2.6 Fetch Syntax Fix

## 수정 내용

`automation/scripts/fetch_realtime_holdings_prices_and_naver_news.py`에서 발생한 f-string 문법 오류를 수정했습니다.

오류 원인:

```text
f-string 내부에서 HTML 링크 문자열을 다시 조립하면서 따옴표가 중첩되어 SyntaxError 발생
```

수정 방식:

```text
기사 링크 HTML을 별도 변수로 만든 뒤 카드 HTML에 삽입하도록 변경
```

## 유지되는 기능

- 보유종목 현재가 네이버 금융 직접 조회
- 네이버뉴스 상세 API 직접 조회
- 추천 종목 분석
- Gemini PM Only
- 엑셀 다운로드 챕터
- 텔레그램 알림

## 적용 방법

1. 압축을 풉니다.
2. `.github`, `automation` 폴더를 PC의 `stock-report` 폴더에 그대로 덮어씁니다.
3. GitHub Desktop에서 변경사항 확인
4. Summary: `apply v12.2.6 fetch syntax fix`
5. Commit to main
6. Push origin
7. Actions에서 Run workflow 실행

## 확인할 Actions 단계

```text
Fetch REAL holding current prices and REAL Naver news detail
Build recommendation candidate analysis
Publish Excel download files
Send Telegram report alert
```
