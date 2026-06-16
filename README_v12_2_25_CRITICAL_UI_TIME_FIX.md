# v12.2.25 Critical UI + Time Fix

## 핵심 수정

1. workflow schedule을 UTC cron으로 복구했습니다.
   - AM 08:00 KST → `0 23 * * 0-4`
   - PM 16:45 KST → `45 7 * * 1-5`
2. `timezone: Asia/Seoul` 라인은 제거했습니다.
3. 워크플로우 초반 Bash Time Guard가 `SKIP_HEAVY_JOB=true/false`를 계산합니다.
4. 지연 실행/주말 schedule은 heavy job을 차단하고 Telegram에 `⚠️ [스케줄 실행 자동 차단 알림]`을 보냅니다.
5. 보유종목 페이지 `docs/v11_holdings/index.html`을 가로 테이블에서 모바일 세로 카드 UI로 변경했습니다.
6. legacy 테이블 렌더링을 모바일 카드형으로 바꿔 가로 스크롤 의존도를 제거했습니다.
7. 추천 TOP15는 미니 리서치 노트형 카드로 표시됩니다.
8. `news_quality_score()`를 독립 스코어링 함수로 강화했습니다.
9. 단순 시세 중계 기사는 -35점, 실적/수주/공시/배당 등 펀더멘탈 기사는 +15점 클러스터 가점을 적용합니다.
10. ETF/알파뉴메릭 종목코드도 `.zfill(6)` 처리합니다.
11. 네이버 현재가 파싱은 일반 주식/ETF 영역을 모두 시도하는 다중 정규식 구조로 변경했습니다.
12. 보유종목 AI 브리핑은 6대 실전 액션 헤드라인을 강제합니다.

## 적용 방법

1. 압축 해제
2. `.github`, `automation`, `.gitignore`를 stock-report repo 루트에 덮어쓰기
3. GitHub Desktop에서 변경사항 확인
4. zip / .env / secrets / stock_report/reports / 대량 xlsx / ipynb 커밋 금지
5. Commit: `apply v12.2.25 critical ui time fix`
6. Push origin
