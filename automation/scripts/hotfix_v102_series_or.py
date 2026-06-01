#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v10.2 HOTFIX
- Fixes pandas "truth value of a Series is ambiguous" error in the notebook.
- Target bug:
    item = map_by_key.get(key) or map_by_key.get(str(name).strip() if name else '')
- Why:
    map_by_key.get(key) returns a pandas Series, and Python `or` tries to evaluate it as True/False.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


BAD_LINE = "item = map_by_key.get(key) or map_by_key.get(str(name).strip() if name else '')"

GOOD_BLOCK = """item = map_by_key.get(key)
        if item is None:
            fallback_key = str(name).strip() if name else ''
            item = map_by_key.get(fallback_key)"""


def patch_notebook(notebook_path: str) -> int:
    path = Path(notebook_path)
    if not path.exists():
        print(f"❌ HOTFIX 실패: 노트북 파일을 찾지 못했습니다: {path}")
        return 1

    nb = json.loads(path.read_text(encoding="utf-8"))
    changed = False
    found_target_area = False

    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue

        source = cell.get("source", [])
        if isinstance(source, list):
            text = "".join(source)
        else:
            text = str(source)

        if "_v102_add_columns_to_sheet" in text:
            found_target_area = True

        if BAD_LINE in text:
            text = text.replace(BAD_LINE, GOOD_BLOCK)
            cell["source"] = text.splitlines(keepends=True)
            changed = True

    if changed:
        path.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
        print("✅ HOTFIX 완료: v10.2 pandas Series fallback 오류 수정")
        return 0

    if found_target_area and "fallback_key = str(name).strip() if name else ''" in json.dumps(nb, ensure_ascii=False):
        print("✅ HOTFIX 확인: 이미 수정된 상태입니다.")
        return 0

    print("⚠️ HOTFIX 경고: 대상 코드를 찾지 못했습니다. 노트북 구조가 바뀌었을 수 있습니다.")
    print("   그래도 실행은 계속합니다. 같은 오류가 다시 나면 로그를 확인하세요.")
    return 0


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) >= 2 else "_runtime_report.ipynb"
    raise SystemExit(patch_notebook(target))
