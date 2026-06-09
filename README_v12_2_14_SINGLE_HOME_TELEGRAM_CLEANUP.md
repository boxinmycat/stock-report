# v12.2.14 Single Home + Telegram Cleanup

## 변경 사항

- `/mobile/`을 단일 홈으로 유지합니다.
- `/latest/`는 별도 홈으로 쓰지 않고 `/mobile/`로 즉시 이동합니다.
- 텔레그램 메시지에서는 `모바일 홈`과 `통합 홈` 두 개를 나누어 보내지 않고 `통합 홈` 1개만 보냅니다.

## 적용
1. 압축을 풉니다.
2. `.github`, `automation` 폴더를 `stock-report` 폴더에 덮어씁니다.
3. Commit 메시지 예시: `apply v12.2.14 single home telegram cleanup`
4. Push 후 workflow 실행
