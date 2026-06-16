# v12.2.28 Toss Account Auto Discovery Hotfix

## 왜 필요한가

토스증권에서 발급되는 앱 키는 보통 아래 2개입니다.

```text
TOSSINVEST_CLIENT_ID
TOSSINVEST_CLIENT_SECRET
```

`TOSSINVEST_ACCOUNT`는 API 키가 아니라, 계좌/자산/주문 조회 API 호출 시 필요한 `X-Tossinvest-Account` 헤더값입니다.

## 수정 내용

v12.2.27에서는 `TOSSINVEST_ACCOUNT`를 Secret으로 넣는 것을 권장했지만, 이 값이 따로 발급 키처럼 보일 수 있어 혼동이 있었습니다.

v12.2.28에서는 다음처럼 바꿨습니다.

```text
1. CLIENT_ID / CLIENT_SECRET만 있어도 실행
2. TOSSINVEST_ACCOUNT가 없으면 accounts API를 먼저 조회
3. 조회된 첫 계좌 식별값을 X-Tossinvest-Account로 자동 사용
4. 자동 조회 실패 시 기존처럼 안전하게 status CSV에 ERROR를 남기고 fallback
```

## GitHub Secrets에 필요한 값

필수:

```text
TOSSINVEST_CLIENT_ID
TOSSINVEST_CLIENT_SECRET
```

선택:

```text
TOSSINVEST_ACCOUNT
```

`TOSSINVEST_ACCOUNT`는 자동 탐색이 안 될 때만 나중에 추가하면 됩니다.

## 적용 방법

1. zip 압축 해제
2. `01_REPO_FILES_TO_EDIT_AND_RETURN` 안의 `.github`, `automation`, `.gitignore`를 stock-report 루트에 덮어쓰기
3. GitHub Secrets에는 우선 CLIENT_ID / CLIENT_SECRET 2개만 등록
4. Commit summary: `apply v12.2.28 toss account auto discovery`
5. Push origin
