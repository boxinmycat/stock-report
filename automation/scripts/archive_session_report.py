#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Archive AM/PM session report v10.6
- Keeps morning and afternoon reports separately.
- Copies docs/reports/YYYYMMDD to docs/reports/YYYYMMDD_AM or YYYYMMDD_PM.
- Updates docs/index.html to latest report and creates docs/reports_index.html.
"""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo


def _session_suffix() -> str:
    mode = os.getenv("REPORT_RUN_MODE", "")
    if mode == "AM_PREMARKET":
        return "AM"
    if mode == "PM_CLOSE":
        return "PM"
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    return "AM" if now.hour < 12 else "PM"


def archive_session():
    reports = []
    for p in Path("docs/reports").glob("20??????"):
        if p.is_dir() and re.fullmatch(r"20\d{6}", p.name):
            reports.append(p)
    if not reports:
        print("⚠️ archive_session: 기본 날짜 리포트 폴더가 없습니다.")
        return
    src = max(reports, key=lambda p: p.stat().st_mtime)
    suffix = _session_suffix()
    dst = src.parent / f"{src.name}_{suffix}"

    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    print(f"✅ session archive: {src} -> {dst}")

    # Latest index points to archived session.
    latest_index = dst / "index.html"
    if latest_index.exists():
        shutil.copy2(latest_index, Path("docs/index.html"))

    items = []
    for p in sorted(Path("docs/reports").glob("20??????_*"), reverse=True):
        if (p / "index.html").exists():
            label = p.name.replace("_AM", " 장전").replace("_PM", " 장마감")
            items.append(f'<li><a href="reports/{p.name}/index.html">{label}</a></li>')

    html = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>Stock Report Index</title>
<style>body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans KR",sans-serif;background:#f5f7fb;margin:0;padding:32px}}main{{max-width:840px;margin:auto;background:white;border-radius:18px;padding:24px}}a{{color:#1d4ed8;font-weight:700;text-decoration:none}}li{{margin:10px 0}}</style></head>
<body><main><h1>Stock Report Archive</h1><p>장전/장마감 리포트 보관 목록입니다.</p><ul>{''.join(items)}</ul></main></body></html>"""
    Path("docs/reports_index.html").write_text(html, encoding="utf-8")


if __name__ == "__main__":
    archive_session()
