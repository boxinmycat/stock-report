# v12.2.13 Push / Schedule / Gemini Health Fix

## 해결하는 문제

1. GitHub push 실패
   - `v9_9_automation_package_20260610.zip`, `html_report_package_20260610.zip`가 100MB를 넘어서 GitHub push가 거절되는 문제를 막습니다.
   - workflow가 생성한 `.zip` 파일을 커밋 대상에서 제외하고, staging 전에 삭제합니다.

2. 아침 리포트 예약 점검
   - 장전 리포트는 08:30 KST 기준입니다.
   - GitHub cron은 UTC 기준으로 `30 23 * * 0-4`를 사용합니다.
   - 장마감 리포트는 16:05 KST 기준이며 UTC cron은 `5 7 * * 1-5`입니다.

3. Gemini API 점검
   - `automation/scripts/check_gemini_api.py`를 추가했습니다.
   - 장마감 또는 수동 실행 때 Gemini API key/model 연결 상태를 확인하고 `docs/data/latest_gemini_health.csv`에 기록합니다.

## 적용 방법

1. 압축을 풉니다.
2. `.github`, `automation`, `.gitignore`를 PC의 `stock-report` 폴더에 그대로 덮어씁니다.
3. GitHub Desktop에서 변경사항 확인
4. Summary: `apply v12.2.13 push schedule gemini health fix`
5. Commit to main
6. Push origin
7. Actions에서 Run workflow 실행

## 추가로 중요

이미 GitHub Desktop 변경사항에 `v9_9_automation_package_20260610.zip` 또는 `html_report_package_20260610.zip`가 보이면, 그 파일들은 커밋하지 말고 Discard 하세요. 이번 패치 이후 workflow에서는 zip을 자동 커밋하지 않습니다.
