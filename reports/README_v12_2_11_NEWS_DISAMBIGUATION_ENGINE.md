# v12.2.11 News Disambiguation Engine

## 목적

태웅/태웅식품 같은 특정 예외 하나만 막는 것이 아니라, 앞으로 모든 추천/보유 종목 뉴스 검색에서 유사명·동명이슈 오매칭을 줄이는 공통 뉴스 매칭 엔진을 추가합니다.

## 핵심 변경

- `automation/scripts/stock_news_disambiguation.py` 신규 추가
- 종목명/종목코드/ETF 여부/뉴스 문맥 기반 점수화
- 짧은 종목명은 더 엄격하게 필터링
- 일반적인 접미어 오매칭 공통 차단: 식품, 푸드, 로직스, 바이오, 제약, 홀딩스 등
- ETF는 개별 기업이 아니라 ETF로 분류
- 네이버뉴스 검색 쿼리를 종목명 단독이 아니라 `주식`, `주가`, `실적`, `공시`, `종목코드` 문맥으로 보강
- 보유종목/Gemini 브리핑/추천 TOP15 기본 설명에서 같은 엔진 사용

## 비용 영향

Gemini 호출은 늘리지 않습니다. 네이버뉴스 API는 검색어가 더 정밀해지면서 종목 수에 따라 호출 수가 소폭 늘 수 있지만, 현재 자동 리포트 규모에서는 한도 부담보다 오매칭 방지 효과가 더 큽니다.

## 적용 방법

1. 압축을 풉니다.
2. `.github`, `automation` 폴더를 PC의 `stock-report` 폴더에 그대로 덮어씁니다.
3. GitHub Desktop에서 변경사항 확인
4. Summary: `apply v12.2.11 news disambiguation engine`
5. Commit to main
6. Push origin
7. Actions에서 Run workflow 실행
