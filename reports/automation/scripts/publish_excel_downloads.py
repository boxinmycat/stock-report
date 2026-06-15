#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone, timedelta
import csv
import html
import re
import shutil

KST = timezone(timedelta(hours=9))

def now():
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")

def safe_name(name: str) -> str:
    base = Path(name).stem
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("_")
    return base[:80] or "stock_report"

def find_xlsx_files():
    roots = [Path("."), Path("stock_report"), Path("docs")]
    files = []
    seen = set()
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*.xlsx"):
            if not p.is_file():
                continue
            # Avoid copying files already published to downloads.
            if "docs/downloads" in p.as_posix():
                continue
            key = p.resolve()
            if key in seen:
                continue
            seen.add(key)
            files.append(p)
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files

def write_csv(rows, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["label", "filename", "url", "source", "size_kb", "published_at"])
        w.writeheader()
        for r in rows:
            w.writerow(r)

def build_index(rows, latest_url):
    links = ""
    for r in rows:
        links += f"""
        <a class="card" href="{html.escape(r['url'])}" download>
          <strong>{html.escape(r['label'])}</strong>
          <span>{html.escape(r['size_kb'])} KB</span>
          <small>원본: {html.escape(r['source'])}</small>
        </a>
        """

    if not links:
        links = "<p>아직 다운로드 가능한 엑셀 파일을 찾지 못했습니다. workflow의 엑셀 생성 단계를 확인하세요.</p>"

    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>엑셀/상세파일 다운로드</title>
<style>
body{{margin:0;background:#f6f7fb;color:#111827;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
.wrap{{max-width:860px;margin:auto;padding:20px}}
.hero{{background:#0f172a;color:white;border-radius:22px;padding:22px;margin-bottom:16px}}
.hero p{{color:#d1d5db;line-height:1.55}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}}
.card{{display:flex;flex-direction:column;gap:6px;background:white;color:#111827;text-decoration:none;border-radius:18px;padding:18px;box-shadow:0 4px 16px rgba(0,0,0,.06)}}
.card span{{color:#2563eb;font-weight:700}}
.card small{{color:#6b7280;line-height:1.4}}
.note{{font-size:13px;color:#6b7280;line-height:1.6;margin-top:14px}}
a{{color:#2563eb}}
</style>
</head>
<body>
<main class="wrap">
<section class="hero">
<h1>엑셀/상세파일 다운로드</h1>
<p>갱신: {html.escape(now())}<br>최신 전체 엑셀 1개를 기본으로 제공합니다. 아래 백업 파일은 원본 후보/이전 산출물 확인용이며, 보통은 최신 전체 엑셀만 받으면 됩니다.</p>
</section>
<section class="grid">
{links}
</section>
<p class="note">가장 최신 엑셀은 <a href="{html.escape(latest_url)}" download>latest_stock_report.xlsx</a>로 고정 저장됩니다. 파일명이 깨지거나 한글명이 복잡해도 이 링크를 사용하면 됩니다.</p>
</main>
</body>
</html>
"""

# Output page: docs/downloads/index.html

def main():
    downloads = Path("docs/downloads")
    downloads.mkdir(parents=True, exist_ok=True)

    xlsx_files = find_xlsx_files()
    rows = []

    if xlsx_files:
        latest = xlsx_files[0]
        stable = downloads / "latest_stock_report.xlsx"
        shutil.copy2(latest, stable)

        rows.append({
            "label": "최신 전체 엑셀 리포트",
            "filename": stable.name,
            "url": "./latest_stock_report.xlsx",
            "source": latest.as_posix(),
            "size_kb": str(round(stable.stat().st_size / 1024, 1)),
            "published_at": now(),
        })

        for i, src in enumerate(xlsx_files[1:5], start=1):
            dst_name = f"stock_report_{i}_{safe_name(src.name)}.xlsx"
            dst = downloads / dst_name
            shutil.copy2(src, dst)
            rows.append({
                "label": f"최근 원본 백업 {i}",
                "filename": dst.name,
                "url": f"./{dst.name}",
                "source": src.as_posix(),
                "size_kb": str(round(dst.stat().st_size / 1024, 1)),
                "published_at": now(),
            })

    write_csv(rows, Path("docs/data/latest_downloads.csv"))

    latest_url = "./latest_stock_report.xlsx" if xlsx_files else "#"
    (downloads / "index.html").write_text(build_index(rows, latest_url), encoding="utf-8")

    print("✅ Excel download files published")
    print(f"xlsx_found: {len(xlsx_files)}")
    if xlsx_files:
        print(f"latest_source: {xlsx_files[0]}")
        print("stable_download: docs/downloads/latest_stock_report.xlsx")

if __name__ == "__main__":
    main()
