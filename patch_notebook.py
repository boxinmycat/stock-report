# -*- coding: utf-8 -*-
import json
from pathlib import Path

# 1. 수리 대상 주피터 노트북 파일명 지정
notebook_filename = "실전매매_통합시스템_v10_2_연속추천관찰_자동조건검색_드라이브준비.ipynb"
nb_path = Path(notebook_filename)

if not nb_path.exists():
    print(f"❌ 에러: [{notebook_filename}] 파일을 찾을 수 없습니다. 프로젝트 루트 폴더에서 실행해 주세요.")
    exit(1)

print(f"⚙️ [{notebook_filename}] 파일 분석 및 정밀 수리를 시작합니다...")

# 2. 노트북 파일 내용 로드
try:
    with open(nb_path, "r", encoding="utf-8") as f:
        nb_data = json.load(f)
except Exception as e:
    print(f"❌ 파일을 읽는 중 오류가 발생했습니다: {e}")
    exit(1)

broken_line = "item = map_by_key.get(key) or map_by_key.get(str(name).strip() if name else '')"
# 판다스 Series의 참/거짓 판별(or) 에러를 우회하는 안전한 딕셔너리 키 검증 삼항 연산자로 교체
fixed_line = "item = map_by_key[key] if key in map_by_key else (map_by_key[str(name).strip()] if (name and str(name).strip() in map_by_key) else None)"

fixed_count = 0

# 3. 소스코드 셀 내부를 순회하며 해당 버그 라인 매칭 교체
for cell in nb_data.get("cells", []):
    if cell.get("cell_type") == "code":
        source_lines = cell.get("source", [])
        new_lines = []
        for line in source_lines:
            if broken_line in line:
                line = line.replace(broken_line, fixed_line)
                fixed_count += 1
            new_lines.append(line)
        cell["source"] = new_lines

# 4. 수리 완료된 파일 영구 저장
if fixed_count > 0:
    with open(nb_path, "w", encoding="utf-8") as f:
        json.dump(nb_data, f, ensure_ascii=False, indent=1)
    print(f"✅ [수리 완료] 총 {fixed_count}곳의 판다스 문법 버그 라인을 정상 교정하여 저장했습니다!")
else:
    print("⚠️ 경고: 수리할 버그 라인을 찾지 못했거나 이미 수정된 상태입니다.")
