# v12.2.25 Stable UTC Schedule + Price Guard

## 목적

이번 패치는 사용자가 지적한 핵심 문제를 안정화합니다.

1. GitHub Actions `timezone` 키 제거
2. UTC cron 방식으로 복귀
3. 장마감 리포트 16:45 KST 기준으로 변경
4. 늦게 실행된 scheduled run 차단 유지
5. PM_TEST 제거
6. 텔레그램 메시지의 중복 `통합 홈` 제거
7. 노트북 실행 timeout 5400초 → 1800초 축소
8. 추천 TOP15 실시간 가격 검증 추가
9. 가격 불일치 종목은 전략 보류 처리
10. 최종 모바일/상세 페이지에 가격 검증 반영

---

## 1. Schedule 변경

GitHub Actions schedule은 UTC cron을 사용합니다.

```yaml
schedule:
  # 08:00 KST = 23:00 UTC, Sunday-Thursday
  - cron: '0 23 * * 0-4'

  # 16:45 KST = 07:45 UTC, Monday-Friday
  - cron: '45 7 * * 1-5'
```

---

## 2. KST 시간 가드

GitHub가 schedule을 너무 늦게 실행하면 리포트를 만들지 않습니다.

```text
AM 허용: 07:30~10:00 KST
PM 허용: 16:30~18:00 KST
주말 schedule: 차단
수동 실행: 허용
```

예를 들어 16:45 리포트가 새벽 02:28에 늦게 실행되면 차단됩니다.

---

## 3. 가격 검증

새 스크립트가 추가됩니다.

```text
automation/scripts/validate_recommendation_prices.py
```

이 스크립트는 `docs/data/latest_recommendation_top15_full.csv`의 종목코드로 네이버 실시간 가격을 다시 확인합니다.

검증 기준:

```text
리포트 기준 현재가와 실시간 현재가 차이가 15% 이상이면 PRICE_MISMATCH
실시간 가격 확인 실패 시 PRICE_UNAVAILABLE
```

`PRICE_MISMATCH` 또는 `PRICE_UNAVAILABLE`이면:

```text
공격/기준/보수 진입가 숨김
돌파 진입가 숨김
손절 기준가 숨김
익절/손절 전략 숨김
모바일 홈과 TOP15 페이지에 전략 보류 표시
```

특히 `0180V0` 같은 알파벳 포함 ETF 코드는 숫자로 강제 변환하지 않고 원문 보존합니다.

---

## 4. 텔레그램 메시지 정리

기존 중복:

```text
모바일 홈
통합 홈
```

수정:

```text
모바일 홈만 표시
```

그리고 가격 검증 결과도 텔레그램에 추가됩니다.

```text
가격 검증: TOP15 통과
가격 검증 경고: N개 종목 전략 보류
```

---

## 5. Timeout 축소

노트북 실행 timeout을 줄였습니다.

```text
5400초 → 1800초
```

그리고 job 전체 timeout도 추가했습니다.

```yaml
timeout-minutes: 45
```

---

## 6. 적용 방법

1. 압축을 풉니다.
2. `.github`, `automation`, `.gitignore`를 stock-report 폴더에 덮어씁니다.
3. GitHub Desktop에서 변경사항 확인
4. zip / stock_report/reports / ipynb / 대량 xlsx가 보이면 Discard
5. Summary: `apply v12.2.25 stable utc price guard`
6. Commit to main
7. Push origin
8. Actions에서 수동 실행으로 먼저 확인합니다.

---

## 확인 페이지

```text
https://boxinmycat.github.io/stock-report/mobile/
https://boxinmycat.github.io/stock-report/details/legacy_top15.html
https://boxinmycat.github.io/stock-report/details/run_manifest.html
```
