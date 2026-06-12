# v12.2.21 Final Quality Refinement

## 반영 범위

이번 패치는 사용자가 최종 점검에서 요청한 5개 개선을 묶은 품질 개선 버전입니다.

## 1. 추천 TOP15 손절/돌파 표기 개선

대상:

```text
docs/details/legacy_top15.html
```

수정 내용:

- `돌파/손절`처럼 의미가 섞여 보이던 표기를 분리
- `돌파 진입가`
- `손절 기준가`
- 익절/손절 계획은 보기 좋은 2줄 구조 유지
- 손절계획이 비어 있을 때 `손절기준가`를 fallback으로 사용

## 2. 종목 설명 개선

수정 내용:

- 현재가, 실전점수, 진입판정처럼 이미 화면에 있는 중복 정보 제거
- ETF는 투자 컨셉, 노출 산업, 구성종목 방향성을 설명
- 일반 종목은 회사가 무엇을 하는지, 주요 제품/고객/테마/실적 이슈 중심으로 설명
- `ACE 미국우주테크액티브` 같은 ETF는 우주항공·위성·방산·우주 인프라 컨셉으로 설명
- `대원강업` 같은 일반 종목은 자동차용 스프링/시트 부품, 완성차 생산 흐름과 연결해 설명

## 3. 전체 추천 명단 열폭 개선

대상:

```text
docs/details/legacy_full_recommendations.html
```

수정 내용:

- `상세전략가이드` 열을 extra-wide 컬럼으로 확대
- 긴 텍스트 열 폭을 기존보다 더 넓게 조정
- 짧은 숫자/점수 열은 좁게 유지

## 4. 연속추천 기준 안내

대상:

```text
docs/details/legacy_continuous.html
```

수정 내용:

- 페이지 상단에 연속추천/추천횟수 해석 기준 추가
- 수동 실행 횟수가 누적 신뢰도처럼 왜곡될 수 있다는 안내 추가
- 실전 해석 기준은 `거래일 + 정기 세션 AM/PM`으로 봐야 함을 명시
- 하루 여러 번 수동 실행해도 추천일수는 중복 해석하지 않도록 안내

## 5. 백테스트 페이지 개선

대상:

```text
docs/details/legacy_candidate_dashboard_validation.html
```

수정 내용:

- `전략요약` 열을 extra-wide 컬럼으로 확대
- 전략요약은 익절 1줄 + 손절 1줄 구조로 정리
- 계좌 백테스트에는 실제 매매 사례처럼 볼 수 있는 `백테스트 거래 요약` 추가
- 전략 백테스트는 효과 상위 전략 1~2순위를 카드로 먼저 보여줌

## 6. 보유종목 Gemini 브리핑 개선

대상:

```text
docs/details/holding_ai_briefing.html
```

수정 내용:

- `신중하게 대응` 같은 모호한 표현을 줄이도록 프롬프트 수정
- 평균단가, 현재가, 손익률, 손절가, 목표가를 반영하도록 강화
- 보유/부분정리/손절검토/추가매수보류/회복확인 같은 구체 액션 표현 유도
- `직전 판단/매도 복기` 섹션 추가
- 뉴스별 날짜/언론사/품질점수 표시
- fallback 문장도 더 구체적으로 수정

## 7. 뉴스 품질 필터링과 메타 표시

대상:

```text
docs/details/naver_news.html
docs/details/holding_ai_briefing.html
```

수정 내용:

- 뉴스마다 언론사 표시
- 뉴스마다 날짜 표시
- 뉴스 품질점수 표시
- 오래된 단순 주가마감 기사 우선순위 하향
- 실적/공시/수주/증자/자사주/대주주/사업확장 뉴스 우선순위 상향
- 지역지/저품질성 단순 시황 기사는 우선순위 하향

예시:

```text
금호타이어 주가, 5월 19일 4,840원 2.42% 하락 마감
```

이런 오래된 단순 시세 기사는 품질점수를 낮게 부여하고, 보유종목 판단에는 우선 반영하지 않도록 개선했습니다.

## 8. 스케줄 진단 유지

v12.2.20의 스케줄 진단 기능은 유지됩니다.

```text
실행 이벤트
실행 cron
예상 KST
실제 시작 KST
```

## 적용 방법

1. 압축을 풉니다.
2. `.github`, `automation`, `.gitignore`를 PC의 `stock-report` 폴더에 그대로 덮어씁니다.
3. GitHub Desktop에서 변경사항 확인
4. zip / stock_report/reports / ipynb / 대량 xlsx가 보이면 Discard
5. Summary: `apply v12.2.21 final quality refinement`
6. Commit to main
7. Push origin
8. Actions에서 Run workflow 또는 다음 예약 실행 확인

## 확인할 페이지

```text
https://boxinmycat.github.io/stock-report/details/legacy_top15.html
https://boxinmycat.github.io/stock-report/details/legacy_full_recommendations.html
https://boxinmycat.github.io/stock-report/details/legacy_continuous.html
https://boxinmycat.github.io/stock-report/details/legacy_candidate_dashboard_validation.html
https://boxinmycat.github.io/stock-report/details/holding_ai_briefing.html
https://boxinmycat.github.io/stock-report/details/naver_news.html
```
