# 실전매매 통합 시스템 GitHub 자동 리포트 패키지 v10.2

이 패키지는 기존 노트북을 GitHub Actions에서 자동 실행하고, 생성된 HTML/엑셀 리포트를 저장소에 커밋하기 위한 구성 파일입니다.

## 이번 버전 기준

- 기본 후보소스: `HYBRID`
- 의미: `자동조건검색 + TOSS_수동후보.csv`
- `TOSS_수동후보.csv`가 없거나 비어 있어도 실행은 멈추지 않습니다.
- DART/네이버 뉴스 API 키는 선택사항입니다.
- 실제 매매 주문 실행은 포함하지 않습니다. 분석 리포트 생성용입니다.

## 파일 구조

```text
.github/workflows/daily-report.yml        # GitHub Actions 자동 실행 설정
automation/scripts/patch_notebook_config.py
automation/scripts/validate_toss_csv.py
requirements.txt
TOSS_수동후보.csv                         # 실제로 읽는 수동 후보 파일
TOSS_수동후보_예시.csv                    # 작성 예시
종목분야_수동입력.csv                     # 선택: 분야 보정 파일
GITHUB_적용방법_상세.md
SECURITY_주의사항.md
docs/.gitkeep
```

## 가장 먼저 할 일

1. 이 패키지를 압축 해제합니다.
2. 본인 GitHub 저장소 루트에 모든 파일/폴더를 올립니다.
3. 기존 노트북 `.ipynb` 파일도 저장소 루트에 같이 올립니다.
4. `.github/workflows/daily-report.yml`의 `NOTEBOOK_FILE` 값을 실제 노트북 파일명과 맞춥니다.
5. `TOSS_수동후보.csv`에 수동 후보 종목을 입력합니다.
6. GitHub Actions에서 `daily-stock-report`를 수동 실행합니다.

자세한 순서는 `GITHUB_적용방법_상세.md`를 보세요.
