# v10.2 Strong Hotfix

이번 패치는 `ValueError: The truth value of a Series is ambiguous` 오류를 잡기 위한 강제 핫픽스입니다.

## 들어있는 파일

- `.github/workflows/daily-report.yml`
- `automation/scripts/hotfix_v102_series_or.py`

## 적용 방법

1. 이 zip을 압축 해제합니다.
2. 안의 `.github` 폴더와 `automation` 폴더를 GitHub 저장소 루트에 덮어씁니다.
3. 반드시 `Commit changes`를 누릅니다.
4. 아래 두 경로가 열리는지 확인합니다.
   - `.github/workflows/daily-report.yml`
   - `automation/scripts/hotfix_v102_series_or.py`
5. Actions → daily-stock-report → Run workflow 실행합니다.

## 정상 로그

아래 두 단계가 보여야 합니다.

- Hotfix v10.2 pandas Series fallback bug in source notebook
- Hotfix v10.2 pandas Series fallback bug in runtime notebook

둘 중 적어도 하나에서 아래 문구가 나오면 정상입니다.

`✅ HOTFIX 완료: v10.2 pandas Series fallback 오류 수정`
