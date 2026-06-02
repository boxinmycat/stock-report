#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v10.2 emergency hotfix.
Fixes pandas "truth value of a Series is ambiguous" caused by:
    item = map_by_key.get(key) or map_by_key.get(str(name).strip() if name else '')
This script patches a .ipynb file before execution.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

GOOD_BLOCK = """item = map_by_key.get(key)
        if item is None:
            fallback_key = str(name).strip() if name else ''
            item = map_by_key.get(fallback_key)"""

PATTERNS = [
    "item = map_by_key.get(key) or map_by_key.get(str(name).strip() if name else '')",
    'item = map_by_key.get(key) or map_by_key.get(str(name).strip() if name else "")',
]

REGEX_PATTERNS = [
    re.compile(r"item\s*=\s*map_by_key\.get\(key\)\s+or\s+map_by_key\.get\(str\(name\)\.strip\(\)\s+if\s+name\s+else\s+['\"]{0,1}['\"]{0,1}\)"),
]


def patch_text(text: str) -> tuple[str, bool]:
    changed = False
    for bad in PATTERNS:
        if bad in text:
            text = text.replace(bad, GOOD_BLOCK)
            changed = True
    for pattern in REGEX_PATTERNS:
        text, n = pattern.subn(GOOD_BLOCK, text)
        changed = changed or bool(n)
    return text, changed


def patch_notebook(notebook_path: str) -> int:
    path = Path(notebook_path)
    if not path.exists():
        print(f"❌ HOTFIX 실패: 노트북 파일을 찾지 못했습니다: {path}")
        return 1

    try:
        nb = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"❌ HOTFIX 실패: 노트북 JSON을 읽지 못했습니다: {path} / {exc}")
        return 1

    changed = False
    found_area = False

    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        source = cell.get("source", [])
        text = "".join(source) if isinstance(source, list) else str(source)

        if "_v102_add_columns_to_sheet" in text or "map_by_key.get(key)" in text:
            found_area = True

        new_text, did_change = patch_text(text)
        if did_change:
            cell["source"] = new_text.splitlines(keepends=True)
            changed = True

    if changed:
        path.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"✅ HOTFIX 완료: {path} 안의 pandas Series fallback 오류 수정")
        return 0

    whole = json.dumps(nb, ensure_ascii=False)
    if "fallback_key = str(name).strip() if name else ''" in whole:
        print(f"✅ HOTFIX 확인: {path}는 이미 수정된 상태입니다.")
        return 0

    if found_area:
        print(f"⚠️ HOTFIX 경고: 관련 영역은 찾았지만 정확한 대상 줄은 찾지 못했습니다: {path}")
    else:
        print(f"⚠️ HOTFIX 경고: v10.2 대상 영역을 찾지 못했습니다: {path}")
    print("같은 오류가 반복되면 노트북 원본의 문제 줄을 직접 교체해야 합니다.")
    return 0


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) >= 2 else "_runtime_report.ipynb"
    raise SystemExit(patch_notebook(target))
