# v12.2.29 Gemini Feedback Merge + Toss Preserved

## 핵심

사용자가 전달한 Gemini 제안의 핵심 개선사항을 반영하되, v12.2.27~28에서 추가된 Toss API read-only 연동과 계좌 자동 탐색 구조는 유지했습니다.

## 반영한 내용

- UTC cron 유지: `0 23 * * 0-4`, `45 7 * * 1-5`
- KST Time Guard 강화
- `SKIP_HEAVY_JOB` 차단 진단 CSV 강화
- Toss API snapshot 단계 유지
- 보유종목 카드에 `AI 매니저의 실전 조언` 블록 연동
- 뉴스 카드에 `뉴스 핵심 3줄 요약` 블록 보강
- 보유종목 AI 브리핑 모호한 표현 필터링 강화
- 추천종목 Gemini 프롬프트에서 숫자 앵무새/공공재 업종 소개 금지 강화
- `legacy_candidate_dashboard_validation.html` 링크/생성 제거 유지

## 적용

1. zip 압축 해제
2. `01_REPO_FILES_TO_EDIT_AND_RETURN` 안의 `.github`, `automation`, `.gitignore`를 stock-report 루트에 덮어쓰기
3. GitHub Desktop에서 변경사항 확인
4. Commit summary: `apply v12.2.29 gemini feedback merge`
5. Push origin
