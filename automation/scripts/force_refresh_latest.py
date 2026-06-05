#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone, timedelta
import html
import os

KST = timezone(timedelta(hours=9))

def now_kst() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")

def detect_session() -> str:
    env = (os.environ.get("REPORT_SESSION") or os.environ.get("SESSION") or "").strip().upper()
    if env in {"AM", "PM", "MANUAL"}:
        return env
    hour = datetime.now(KST).hour
    if hour < 12:
        return "AM"
    if hour < 18:
        return "PM"
    return "MANUAL"

def find_latest_report_index() -> Path | None:
    candidates = []
    reports = Path("docs/reports")
    if reports.exists():
        candidates.extend([p for p in reports.rglob("index.html") if p.is_file()])
    root_index = Path("docs/index.html")
    if root_index.exists():
        candidates.append(root_index)
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)

def relative_link_from_latest(target: Path) -> str:
    try:
        rel = target.relative_to(Path("docs"))
        return "../" + rel.as_posix()
    except Exception:
        return "../index.html"

def write_mobile_page(stamp: str, session: str) -> None:
    mobile = Path("docs/mobile")
    mobile.mkdir(parents=True, exist_ok=True)
    page = mobile / "index.html"
    links = [
        ("최신 리포트", "../latest/"),
        ("v11 보유종목 대시보드", "../v11_holdings/"),
        ("v11 전략 검증", "../strategy/"),
        ("상세 데이터 센터", "../details/"),
        ("네이버뉴스 상세", "../details/naver_news.html"),
        ("구글시트 CSV 데이터", "../data/"),
    ]
    rows = "\n".join(
        f'<a class="card" href="{html.escape(url)}"><strong>{html.escape(label)}</strong><span>열기</span></a>'
        for label, url in links
    )
    text = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Stock Report Mobile</title>
  <style>
    body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; background:#f6f7fb; color:#111827; }}
    .wrap {{ max-width:860px; margin:0 auto; padding:20px; }}
    .hero {{ background:#111827; color:white; border-radius:22px; padding:22px; margin-bottom:16px; }}
    .hero h1 {{ margin:0 0 8px; font-size:24px; }}
    .meta {{ color:#d1d5db; font-size:14px; line-height:1.6; }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:12px; }}
    .card {{ display:flex; justify-content:space-between; gap:12px; align-items:center; text-decoration:none; background:white; color:#111827; border-radius:18px; padding:18px; box-shadow:0 4px 16px rgba(0,0,0,.06); }}
    .card span {{ color:#2563eb; font-weight:700; }}
    .note {{ margin-top:16px; color:#6b7280; font-size:13px; line-height:1.6; }}
  </style>
</head>
<body>
  <main class="wrap">
    <section class="hero">
      <h1>주식 리포트 모바일 홈</h1>
      <div class="meta">최근 갱신: {html.escape(stamp)}<br>세션: {html.escape(session)}<br>이 페이지는 GitHub Actions 실행 때마다 자동 갱신됩니다.</div>
    </section>
    <section class="grid">
      {rows}
    </section>
    <p class="note">GitHub 앱에서 HTML 파일을 누르면 코드가 보일 수 있습니다. 크롬/사파리에서 이 모바일 주소를 열어 홈 화면에 추가해두면 편합니다.</p>
  </main>
  <!-- mobile-refresh: {html.escape(stamp)} / {html.escape(session)} -->
</body>
</html>
"""
    page.write_text(text, encoding="utf-8")
    print(f"✅ mobile page refreshed: {page}")

def main() -> int:
    stamp = now_kst()
    session = detect_session()
    latest_dir = Path("docs/latest")
    latest_dir.mkdir(parents=True, exist_ok=True)
    latest_file = latest_dir / "index.html"
    source = find_latest_report_index()

    if source and source.resolve() != latest_file.resolve():
        text = source.read_text(encoding="utf-8", errors="ignore")
        source_link = relative_link_from_latest(source)
        banner = f"""
<div style="margin:12px 0;padding:12px 14px;border-radius:12px;background:#eef2ff;color:#1e1b4b;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:14px;">
  <strong>Latest page refreshed:</strong> {html.escape(stamp)} / {html.escape(session)}
  <br><span>source: <a href="{html.escape(source_link)}">{html.escape(source.as_posix())}</a></span>
</div>
"""
        lower = text.lower()
        idx = lower.find("<body")
        if idx >= 0:
            close = text.find(">", idx)
            if close >= 0:
                text = text[: close + 1] + banner + text[close + 1 :]
            else:
                text = banner + text
        else:
            text = banner + text
        text += f"\n<!-- latest-refresh: {stamp} / {session} / source={source.as_posix()} -->\n"
        latest_file.write_text(text, encoding="utf-8")
        print(f"✅ latest refreshed from: {source}")
    else:
        fallback = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Latest Stock Report</title>
</head>
<body>
  <h1>Latest Stock Report</h1>
  <p>최근 갱신: {html.escape(stamp)}</p>
  <p>세션: {html.escape(session)}</p>
  <p>아직 복사할 리포트 index.html을 찾지 못했습니다. workflow 로그에서 리포트 생성 단계를 확인하세요.</p>
  <!-- latest-refresh: {html.escape(stamp)} / {html.escape(session)} / fallback -->
</body>
</html>
"""
        latest_file.write_text(fallback, encoding="utf-8")
        print("⚠️ report index not found; fallback latest page created")

    write_mobile_page(stamp, session)

    data_dir = Path("docs/data")
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "latest_publish_status.csv").write_text(
        "key,value\n"
        f"published_at,{stamp}\n"
        f"session,{session}\n"
        f"latest_file,{latest_file.as_posix()}\n"
        f"source,{source.as_posix() if source else 'not_found'}\n",
        encoding="utf-8-sig",
    )
    print("✅ latest publish status csv written")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
