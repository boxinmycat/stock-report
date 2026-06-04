# v10.6 패치 — 클린 HTML + 네이버뉴스 + OpenAI 선택 해석 + 08/16시 2회 실행

## 들어있는 파일

- `.github/workflows/daily-report.yml`
- `automation/scripts/rebuild_clean_html_report.py`
- `automation/scripts/add_naver_news_summary.py`
- `automation/scripts/archive_session_report.py`

## 적용 순서

1. 압축을 풉니다.
2. GitHub 저장소 루트에 `.github`, `automation` 폴더를 그대로 업로드합니다.
3. Commit changes 합니다.
4. GitHub Secrets에 `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`이 있는지 확인합니다.
5. OpenAI 해석을 쓰려면 `OPENAI_API_KEY`를 Secrets에 추가하고, Repository Variables에 `ENABLE_OPENAI_NEWS_ANALYSIS=true`를 추가합니다.
6. Actions → daily-stock-report → Run workflow로 테스트합니다.

## 실행 시간

- 08:00 KST 월~금: 장전 리포트
- 16:00 KST 월~금: 장마감 리포트

## OpenAI 비용 안전장치

기본값은 OpenAI OFF입니다.
`ENABLE_OPENAI_NEWS_ANALYSIS=true`를 넣지 않으면 OpenAI API를 호출하지 않습니다.

## 리포트 보관

- `docs/reports/YYYYMMDD_AM`
- `docs/reports/YYYYMMDD_PM`

형태로 장전/장마감 리포트를 분리 저장합니다.
