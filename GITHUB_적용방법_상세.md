# GitHub 적용 방법 상세 가이드

지금 너가 하려는 흐름은 이렇게 보면 됩니다.

→ 기존 코랩 노트북은 그대로 둔다  
→ GitHub에는 자동 실행용 설정 파일을 추가한다  
→ 매일 GitHub Actions가 노트북을 실행한다  
→ 결과 HTML/엑셀 파일이 `docs/` 또는 `stock_report/`에 저장된다  
→ GitHub Pages로 `docs/index.html`을 열어본다  

---

## 1단계. 압축 풀기

다운로드한 압축파일을 풀면 아래 구조가 나옵니다.

```text
.github/
automation/
docs/
requirements.txt
TOSS_수동후보.csv
TOSS_수동후보_예시.csv
종목분야_수동입력.csv
README.md
GITHUB_적용방법_상세.md
SECURITY_주의사항.md
```

이 폴더와 파일들을 GitHub 저장소 루트에 그대로 올리면 됩니다.

---

## 2단계. 노트북 파일도 같이 올리기

기존에 쓰던 노트북 파일을 GitHub 저장소 루트에 올립니다.

권장 파일명은 아래와 같습니다.

```text
실전매매_통합시스템_v10_2_연속추천관찰_자동조건검색_드라이브준비.ipynb
```

파일명이 다르면 `.github/workflows/daily-report.yml` 안의 이 줄을 수정합니다.

```yaml
NOTEBOOK_FILE: 실전매매_통합시스템_v10_2_연속추천관찰_자동조건검색_드라이브준비.ipynb
```

예를 들어 실제 파일명이 `my_stock_report.ipynb`라면 이렇게 바꿉니다.

```yaml
NOTEBOOK_FILE: my_stock_report.ipynb
```

---

## 3단계. TOSS 수동 후보 파일 작성

실제로 읽히는 파일은 이것입니다.

```text
TOSS_수동후보.csv
```

기본 파일은 헤더만 있습니다.

```csv
종목명,종목코드,스크리너명,메모
```

후보를 넣을 때는 아래처럼 입력합니다.

```csv
종목명,종목코드,스크리너명,메모
한성크린텍,066980,토스수동후보,예시
```

종목코드는 반드시 6자리로 쓰는 걸 권장합니다.

좋은 작성 방식은 이렇습니다.

| 컬럼 | 입력 예시 | 설명 |
|---|---|---|
| 종목명 | 한성크린텍 | 종목명 |
| 종목코드 | 066980 | 6자리 종목코드 |
| 스크리너명 | 토스 저평가 | 어디서 가져온 후보인지 |
| 메모 | 관심 후보 | 본인 메모 |

이번 패키지는 `HYBRID` 기준이라서, 이 파일이 있으면 자동조건검색 후보와 함께 반영됩니다. 파일이 비어 있으면 자동조건검색만 실행됩니다.

---

## 4단계. GitHub Secrets 설정

GitHub 저장소에서 아래 순서로 들어갑니다.

```text
Settings
→ Secrets and variables
→ Actions
→ New repository secret
```

선택적으로 아래 값을 넣습니다.

| Secret 이름 | 필수 여부 | 설명 |
|---|---|---|
| `OPEN_DART_API_KEY` | 선택 | DART 재무 데이터 보강 |
| `NAVER_CLIENT_ID` | 선택 | 네이버 뉴스 API |
| `NAVER_CLIENT_SECRET` | 선택 | 네이버 뉴스 API |

키가 없어도 기본 리포트는 실행되도록 구성했습니다. 다만 재무 성장률/뉴스 보강 품질은 떨어질 수 있습니다.

절대 API 키를 노트북 코드나 CSV 파일에 직접 적지 마세요.

---

## 5단계. GitHub Actions 수동 실행

저장소 상단 메뉴에서 아래 순서로 들어갑니다.

```text
Actions
→ daily-stock-report
→ Run workflow
→ 초록색 Run workflow 클릭
```

처음 실행은 반드시 수동 실행으로 확인하는 게 좋습니다.

성공하면 저장소에 아래 결과가 생깁니다.

```text
docs/index.html
docs/reports/YYYYMMDD/index.html
YYYYMMDD.xlsx
또는 stock_report/...
```

노트북 구조에 따라 결과 저장 위치가 조금 다를 수 있습니다. 이번 워크플로우는 `docs`, `stock_report`, `*.xlsx`, `*.zip`을 커밋 대상으로 잡아두었습니다.

---

## 6단계. GitHub Pages 설정

저장소에서 아래로 들어갑니다.

```text
Settings
→ Pages
```

설정은 이렇게 잡습니다.

```text
Source: Deploy from a branch
Branch: main
Folder: /docs
Save
```

GitHub Pages는 `/docs` 폴더를 배포 소스로 사용할 수 있습니다. 그래서 노트북이 `docs/index.html`을 만들면 그 파일이 홈페이지 첫 화면이 됩니다.

---

## 7단계. 매일 자동 실행 시간

현재 설정은 아래와 같습니다.

```yaml
cron: '30 23 * * 0-5'
```

이건 UTC 기준 23:30이고, 한국시간으로는 다음 날 08:30입니다.

즉 한국 장 시작 전 확인용으로 맞춰둔 값입니다.

---

## 8단계. 자주 나는 오류

### 1. Notebook file not found

원인: `.github/workflows/daily-report.yml`의 `NOTEBOOK_FILE` 이름과 실제 파일명이 다릅니다.

해결: 실제 업로드한 `.ipynb` 파일명으로 수정합니다.

---

### 2. No module named ...

원인: 필요한 패키지가 `requirements.txt`에 없습니다.

해결: 오류에 나온 패키지명을 `requirements.txt`에 한 줄 추가합니다.

예:

```text
패키지명
```

---

### 3. TOSS CSV column error

원인: `TOSS_수동후보.csv` 헤더가 바뀌었습니다.

해결: 첫 줄을 아래처럼 맞춥니다.

```csv
종목명,종목코드,스크리너명,메모
```

---

### 4. GitHub Pages 화면이 안 뜸

확인 순서:

```text
1. Actions 실행 성공 여부 확인
2. docs/index.html 생성 여부 확인
3. Settings → Pages → main / docs 설정 확인
4. 1~3분 정도 기다린 뒤 새로고침
```

---

## 9단계. 운영 방식

매일 흐름은 이렇게 잡으면 됩니다.

```text
08:30 GitHub 자동 실행
        ↓
docs/index.html 확인
        ↓
시장브리핑 확인
        ↓
보유종목_진단 확인
        ↓
저평가성장주_조건검색 확인
        ↓
TOSS 수동 후보가 반영됐는지 확인
        ↓
실제 매매 전 HTS/MTS에서 호가·뉴스·공시 최종 확인
```

이 패키지는 자동 주문 시스템이 아니라 분석 리포트 자동 생성 시스템입니다.
