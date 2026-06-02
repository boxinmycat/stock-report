적용 방법:
1) 압축을 푼다.
2) .github 폴더와 automation 폴더를 GitHub 저장소 루트에 Upload files 방식으로 덮어쓴다.
3) Create new file로 붙여넣지 말고, 반드시 파일 업로드 방식으로 올린다.
4) Commit changes를 누른다.
5) raw 파일에서 줄바꿈이 살아있는지 확인한다.

확인 경로:
https://raw.githubusercontent.com/boxinmycat/stock-report/main/.github/workflows/daily-report.yml
https://raw.githubusercontent.com/boxinmycat/stock-report/main/automation/scripts/hotfix_v102_series_or.py

raw 파일이 한 줄이면 실패다. 여러 줄로 보여야 정상이다.
