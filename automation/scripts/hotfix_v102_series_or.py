#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


BAD_EXACT = "item = map_by_key.get(key) or map_by_key.get(str(name).strip() if name else '')"

GOOD_BLOCK = """item = map_by_key.get(key)
        if item is None:
            fallback_key = str(name).strip() if name else ''
            item = map_by_key.get(fallback_key)"""

BAD_REGEX = re.compile(
    r"item\s*=\s*map_by_key\.get\(\s*key\s*\)\s*or\s*map_by_key\.get\(\s*str\(name\)\.strip\(\)\s*if\s*name\s*else\s*''\s*\)"
)


def _cell_to_text(source) -> str:
    if isinstance(source, list):
        return "".join(source)
    return str(source)


def _text_to_source(text: str):
    return text.splitlines(keepends=True)


def patch_notebook(notebook_path: str) -> int:
    path = Path(notebook_path)

    if not path.exists():
        print(f"❌ HOTFIX 실패: 노트북 파일을 찾지 못했습니다: {path}")
        return 1

    try:
        nb = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"❌ HOTFIX 실패: 노트북 JSON을 읽지 못했습니다: {path} / {e}")
        return 1

    changed = False
    target_area_found = False
    already_fixed = False

    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue

        text = _cell_to_text(cell.get("source", []))

        if "_v102_add_columns_to_sheet" in text or "map_by_key.get(key)" in text:
            target_area_found = True

        if "fallback_key = str(name).strip() if name else ''" in text:
            already_fixed = True

        new_text = text

        if BAD_EXACT in new_text:
            new_text = new_text.replace(BAD_EXACT, GOOD_BLOCK)

        new_text = BAD_REGEX.sub(GOOD_BLOCK, new_text)

        if new_text != text:
            cell["source"] = _text_to_source(new_text)
            changed = True

    if changed:
        path.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
        print("✅ HOTFIX 완료: v10.2 pandas Series fallback 오류 수정")
        return 0

    if already_fixed:
        print("✅ HOTFIX 확인: 이미 수정된 상태입니다.")
        return 0

    if target_area_found:
        print("⚠️ HOTFIX 경고: v10.2 함수 영역은 찾았지만 정확한 오류 줄은 찾지 못했습니다.")
        print("노트북 코드가 이전 패치와 다른 형태일 수 있습니다.")
        return 0

    print("⚠️ HOTFIX 경고: v10.2 연속추천 패치 영역을 찾지 못했습니다.")
    print("그래도 실행은 계속합니다.")
    return 0


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) >= 2 else "_runtime_report.ipynb"
    raise SystemExit(patch_notebook(target))
