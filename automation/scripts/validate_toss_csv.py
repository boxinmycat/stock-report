"""
Validate TOSS_수동후보.csv for GitHub Actions.

필수 컬럼
- 종목명
- 종목코드

선택 컬럼
- 스크리너명
- 메모

파일이 없으면 빈 헤더 파일을 생성합니다.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path


REQUIRED = ["종목명", "종목코드"]
DEFAULT_HEADER = ["종목명", "종목코드", "스크리너명", "메모"]


def main() -> None:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "TOSS_수동후보.csv")

    if not path.exists():
        path.write_text(",".join(DEFAULT_HEADER) + "\n", encoding="utf-8-sig")
        print(f"ℹ️ {path} 파일이 없어 빈 템플릿을 생성했습니다.")
        return

    text = path.read_text(encoding="utf-8-sig").strip()
    if not text:
        path.write_text(",".join(DEFAULT_HEADER) + "\n", encoding="utf-8-sig")
        print(f"ℹ️ {path} 파일이 비어 있어 헤더를 다시 생성했습니다.")
        return

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

    missing = [c for c in REQUIRED if c not in fields]
    if missing:
        raise SystemExit(
            f"❌ {path} 컬럼 오류: {missing} 컬럼이 필요합니다.\n"
            f"현재 컬럼: {fields}\n"
            "권장 헤더: 종목명,종목코드,스크리너명,메모"
        )

    print(f"✅ {path} 확인 완료. 컬럼: {fields}")


if __name__ == "__main__":
    main()
