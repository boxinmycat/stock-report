# v12.2.22 Gemini Recommendation Profiles

## 목적

추천 종목 설명을 단순 업종 설명이 아니라, 사용자가 예시로 제시한 수준의 `미니 리서치 노트` 형태로 고도화합니다.

## 새 스크립트

```text
automation/scripts/build_gemini_recommendation_company_profiles.py
```

이 스크립트는 추천 TOP15를 읽고 Gemini API로 종목별 설명을 생성합니다.

## 생성되는 설명 구조

```text
🤖 분석 컨셉
📌 한 줄 요약
🚀 핵심 포인트
📦 사업/구성 포인트
⚠️ 주의 리스크
```

## ETF 설명 방식

ETF는 단순히 “ETF 상품입니다”로 끝내지 않고 다음을 설명합니다.

```text
- 어떤 컨셉의 ETF인지
- 어떤 산업/자산군에 노출되는지
- 구성종목 또는 주요 노출 분야
- 액티브/테마형 ETF로서 봐야 할 리스크
```

## 개별 종목 설명 방식

개별 종목은 단순 업종명 반복을 피하고 다음을 설명합니다.

```text
- 회사가 실제로 무엇을 하는지
- 주요 제품/고객사/전방산업
- 최근 실적·공시·테마·수급 포인트
- Bull / Bear 포인트
```

## 중복 제거

다음 정보는 이미 표에 있으므로 종목 설명에서는 반복하지 않도록 프롬프트를 조정했습니다.

```text
현재가
실전점수
진입판정
익절/손절 수치
```

## Workflow 변경

`Restore legacy Excel report sections` 다음에 아래 단계가 추가됩니다.

```yaml
- name: Build Gemini recommendation company profiles
  run: |
    python automation/scripts/build_gemini_recommendation_company_profiles.py
```

이 단계는 프로필을 만든 뒤 legacy 페이지를 다시 빌드해서 TOP15 페이지에 깊은 설명이 반영되게 합니다.

## 생성 파일

```text
docs/data/latest_recommendation_company_profiles.csv
docs/data/latest_recommendation_profile_status.csv
```

## 적용 방법

1. 압축을 풉니다.
2. `.github`, `automation`, `.gitignore`를 PC의 `stock-report` 폴더에 그대로 덮어씁니다.
3. GitHub Desktop에서 변경사항 확인
4. zip / stock_report/reports / ipynb / 대량 xlsx가 보이면 Discard
5. Summary: `apply v12.2.22 gemini recommendation profiles`
6. Commit to main
7. Push origin
8. Actions에서 Run workflow 또는 다음 예약 실행 확인

## 확인 페이지

```text
https://boxinmycat.github.io/stock-report/details/legacy_top15.html
https://boxinmycat.github.io/stock-report/details/legacy_entry_scenario.html
```
