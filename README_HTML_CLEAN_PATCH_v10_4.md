# v10.4 HTML 브리핑 정리 패치

## 문제
HTML 브리핑에 `Name: 44, dtype: object`, `NaN` 같은 pandas 내부 출력이 그대로 들어가는 문제를 막습니다.

## 적용 파일
- `automation/scripts/rebuild_clean_html_report.py`

## workflow에 추가할 위치
`.github/workflows/daily-report.yml`에서 아래 단계 바로 뒤에 넣으세요.

```yaml
      - name: Run report notebook
        run: |
          jupyter nbconvert --to notebook --execute "_runtime_report.ipynb" --output executed_report.ipynb --ExecutePreprocessor.timeout=5400

      - name: Rebuild clean HTML briefing report
        run: |
          python automation/scripts/rebuild_clean_html_report.py
```

반드시 `Commit generated report` 단계보다 앞에 있어야 합니다.

## 기대 결과
- `docs/index.html`
- `docs/reports/YYYYMMDD/index.html`

두 파일이 깔끔한 HTML 브리핑으로 다시 생성됩니다.
