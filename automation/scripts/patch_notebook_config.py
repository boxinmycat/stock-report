"""
Patch a stock-report notebook for GitHub Actions runtime.

목적
- 기존 노트북 원본은 건드리지 않고 _runtime_report.ipynb를 생성합니다.
- CONFIG 정의 셀 바로 뒤에 GitHub 실행용 설정 셀을 끼워 넣습니다.
- 기본 후보소스는 HYBRID로 강제합니다.
  HYBRID = 자동조건검색 + TOSS_수동후보.csv가 있으면 함께 반영
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from copy import deepcopy


PATCH_MARKER = "# === GITHUB_RUNTIME_CONFIG_PATCH_V10_2_HYBRID_TOSS ==="

PATCH_SOURCE = f"""{PATCH_MARKER}
import os
from pathlib import Path

try:
    CONFIG
except NameError:
    CONFIG = {{}}

# GitHub Actions 실행 기본값
CONFIG['CANDIDATE_SOURCE_MODE'] = os.getenv('CANDIDATE_SOURCE_MODE', 'HYBRID')
CONFIG['UNIVERSE_SOURCE'] = 'HYBRID'  # 구버전 호환
CONFIG['REQUIRE_TOSS_FILE'] = str(os.getenv('REQUIRE_TOSS_FILE', 'false')).lower() == 'true'
CONFIG['ENABLE_AUTO_CONDITION_SEARCH'] = True
CONFIG['FALLBACK_TO_NAVER_WHEN_TOSS_FAIL'] = True

# TOSS 수동 후보 파일
CONFIG['TOSS_MANUAL_CSV_FILE'] = os.getenv('TOSS_MANUAL_CSV_FILE', 'TOSS_수동후보.csv')
CONFIG['TOSS_MANUAL_XLSX_FILE'] = os.getenv('TOSS_MANUAL_XLSX_FILE', '국내 저평가주식 목록 토스.xlsx')

# GitHub에서는 Google Drive 저장을 끄고, 노트북이 생성하는 docs/ 또는 stock_report/ 결과를 커밋합니다.
CONFIG['USE_GOOGLE_DRIVE'] = False
CONFIG['REPORT_ROOT_MODE'] = os.getenv('REPORT_ROOT_MODE', 'LOCAL')
CONFIG['OUTPUT_FILENAME_DATE_ONLY'] = True

# API 키: GitHub Secrets에서 들어오면 CONFIG에도 넣습니다.
_dart_key = os.getenv('OPEN_DART_API_KEY') or os.getenv('DART_API_KEY') or ''
CONFIG['DART_API_KEY'] = _dart_key
CONFIG['OPEN_DART_API_KEY'] = _dart_key
CONFIG['NAVER_CLIENT_ID'] = os.getenv('NAVER_CLIENT_ID', '')
CONFIG['NAVER_CLIENT_SECRET'] = os.getenv('NAVER_CLIENT_SECRET', '')

# TOSS 파일이 없으면 빈 헤더 파일을 만들어 HYBRID 실행이 멈추지 않게 합니다.
_toss_path = Path(CONFIG['TOSS_MANUAL_CSV_FILE'])
if not _toss_path.exists():
    _toss_path.write_text('종목명,종목코드,스크리너명,메모\\n', encoding='utf-8-sig')
    print(f'ℹ️ TOSS 수동 후보 파일이 없어 빈 파일을 생성했습니다: {{_toss_path}}')
else:
    print(f'✅ TOSS 수동 후보 파일 확인: {{_toss_path}}')

print('✅ GitHub runtime CONFIG 적용 완료')
print('   - CANDIDATE_SOURCE_MODE:', CONFIG.get('CANDIDATE_SOURCE_MODE'))
print('   - TOSS_MANUAL_CSV_FILE:', CONFIG.get('TOSS_MANUAL_CSV_FILE'))
"""


def _new_code_cell(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [line + "\n" for line in source.splitlines()],
    }


def _cell_text(cell: dict) -> str:
    src = cell.get("source", "")
    if isinstance(src, list):
        return "".join(src)
    return str(src)


def _find_insert_index(cells: list[dict]) -> int:
    # 1순위: v10.1/v10.2 CONFIG 후보소스 기본값 셀 바로 뒤
    for i, cell in enumerate(cells):
        text = _cell_text(cell)
        if cell.get("cell_type") == "code" and "CANDIDATE_SOURCE_MODE" in text and "CONFIG" in text:
            return i + 1

    # 2순위: CONFIG 딕셔너리 정의 셀 바로 뒤
    for i, cell in enumerate(cells):
        text = _cell_text(cell)
        if cell.get("cell_type") == "code" and ("CONFIG =" in text or "CONFIG={" in text):
            return i + 1

    # 3순위: 첫 코드 셀 뒤
    for i, cell in enumerate(cells):
        if cell.get("cell_type") == "code":
            return i + 1

    return len(cells)


def patch_notebook(input_path: Path, output_path: Path) -> None:
    if not input_path.exists():
        candidates = [
            p for p in Path(".").glob("*.ipynb")
            if not p.name.startswith("_")
            and p.name != output_path.name
            and "executed" not in p.name.lower()
        ]
        if len(candidates) == 1:
            input_path = candidates[0]
            print(f"ℹ️ 지정한 노트북을 찾지 못해 자동 선택했습니다: {input_path}")
        else:
            names = "\n".join(f"- {p.name}" for p in candidates[:20])
            raise FileNotFoundError(
                f"노트북 파일을 찾지 못했습니다: {input_path}\n"
                f"저장소 루트의 ipynb 후보:\n{names}\n\n"
                "해결: .github/workflows/daily-report.yml의 NOTEBOOK_FILE 값을 실제 파일명으로 바꾸세요."
            )

    nb = json.loads(input_path.read_text(encoding="utf-8"))
    cells = nb.get("cells", [])

    # 기존 패치 셀 제거 후 다시 삽입
    cells = [c for c in cells if PATCH_MARKER not in _cell_text(c)]
    insert_at = _find_insert_index(cells)
    cells.insert(insert_at, _new_code_cell(PATCH_SOURCE))

    nb["cells"] = cells
    output_path.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✅ Runtime notebook created: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="원본 ipynb 파일명")
    parser.add_argument("output", help="생성할 runtime ipynb 파일명")
    args = parser.parse_args()

    patch_notebook(Path(args.input), Path(args.output))


if __name__ == "__main__":
    main()
