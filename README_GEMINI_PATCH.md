# v12.2.26 Full Pipeline Refactor + Mobile Cards

## 핵심 반영

1. `legacy_candidate_dashboard_validation.html` 생성 제거
2. GitHub Actions schedule을 UTC cron으로 고정
   - AM: `0 23 * * 0-4` = KST 08:00
   - PM: `45 7 * * 1-5` = KST 16:45
3. KST Time Guard 강화
   - AM 허용: 07:30~10:00
   - PM 허용: 15:45~18:30
   - 주말 schedule 차단
   - workflow_dispatch 수동 실행 허용
4. Heavy job skip 시에도 Telegram 차단 알림 발송
5. `docs/v11_holdings/index.html` 모바일 카드 UI에 AI 매니저 실전 조언 블록 연동
6. `legacy_top15.html`, `legacy_full_recommendations.html`, `legacy_continuous.html` 가로 스크롤 없는 카드 UI 유지/강화
7. `legacy_continuous.html` 출석도장 카드 UI 추가
8. `naver_news.html` 뉴스별 핵심 3줄 요약 블록 추가
9. 보유종목 AI 브리핑 5단계 구조 고정
10. ETF 코드 보정 및 `ACE 미국우주테크액티브 -> 0180V0` 오버라이드 추가

## 적용 방법

1. zip 압축 해제
2. `01_REPO_FILES_TO_EDIT_AND_RETURN` 안의 `.github`, `automation`, `.gitignore`를 stock-report 루트에 덮어쓰기
3. GitHub Desktop에서 변경사항 확인
4. zip / .env / secrets / stock_report/reports / 대량 xlsx / ipynb는 커밋 금지
5. Commit summary: `apply v12.2.26 full pipeline refactor mobile cards`
6. Push origin

## 주의

- HTML 결과물을 직접 수정하지 않고 생성 스크립트를 수정했습니다.
- 실제 Naver/Gemini API 동작은 GitHub Actions에서 한 번 실행해 최종 확인해야 합니다.
