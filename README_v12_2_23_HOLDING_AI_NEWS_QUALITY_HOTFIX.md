# v12.2.23 Holding AI News Quality Hotfix

## 해결하는 오류

GitHub Actions의 `Build Gemini 3.5 Flash holding AI briefing` 단계에서 아래 오류가 발생하는 문제를 수정합니다.

```text
NameError: name 'news_quality_score' is not defined
```

## 원인

`build_gemini_holding_ai_briefing.py`의 `related()` 함수가 뉴스 품질점수 계산을 위해 `news_quality_score()`를 호출하지만, 현재 적용된 파일에서 import/fallback 정의가 빠져 있었습니다.

## 수정 내용

아래 import를 보강했습니다.

```python
from stock_news_disambiguation import filter_and_rank_news, extract_publisher, format_pubdate, news_quality_score
```

그리고 혹시 `stock_news_disambiguation.py`가 구버전이어도 죽지 않도록 local fallback을 추가했습니다.

## 적용 방법

1. 압축을 풉니다.
2. `.github`, `automation`, `.gitignore`를 stock-report 폴더에 덮어씁니다.
3. GitHub Desktop에서 변경사항 확인
4. zip / stock_report/reports / ipynb / 대량 xlsx가 보이면 Discard
5. Summary: `apply v12.2.23 holding ai hotfix`
6. Commit to main
7. Push origin
8. Actions에서 다시 실행합니다.
