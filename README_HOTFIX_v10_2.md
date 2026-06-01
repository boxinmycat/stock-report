# v10.2 HOTFIX - pandas Series ambiguous 오류 수정

## 오류 원인

GitHub Actions 로그에서 아래 줄에서 실패했습니다.

```python
item = map_by_key.get(key) or map_by_key.get(str(name).strip() if name else '')
```

`map_by_key.get(key)`가 pandas Series를 반환하면 Python의 `or`가 Series를 True/False로 판단하려고 해서 아래 오류가 납니다.

```text
ValueError: The truth value of a Series is ambiguous.
```

## 이 패치가 하는 일

노트북 실행 직전에 `_runtime_report.ipynb` 안의 문제 코드를 자동으로 아래처럼 바꿉니다.

```python
item = map_by_key.get(key)
if item is None:
    fallback_key = str(name).strip() if name else ''
    item = map_by_key.get(fallback_key)
```

## 적용 방법

압축을 풀고 아래 파일 2개를 GitHub 저장소 루트 기준으로 업로드/덮어쓰기하세요.

```text
automation/scripts/hotfix_v102_series_or.py
.github/workflows/daily-report.yml
```

그 다음 GitHub Actions에서 `daily-stock-report`를 다시 `Run workflow` 하면 됩니다.
