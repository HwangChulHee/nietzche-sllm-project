"""GM (Genealogy of Morals) 영어 청커.

3개 에세이 + 서문 (preface). 각각 자체 번호 시퀀스.
청크 단위: section 단위 (1단락 = 1청크). 필터 단계에서 자립성 검사로 거름.
Peoples and Countries (Fragment) 부록 제외.
"""
import json
import re
from pathlib import Path
from collections import Counter

INPUT = Path("v2_data/english_raw/the-genealogy-of-morals.txt")
OUTPUT = Path("v2_data/english_chunks/gm.jsonl")

# 에세이 마커 (실제 본문, TOC 아님)
ESSAY_PATTERN = re.compile(r'^(FIRST|SECOND|THIRD)\s+ESSAY\.')
ESSAY_NUM = {'FIRST': 1, 'SECOND': 2, 'THIRD': 3}

# 단락 번호 패턴: 단독 줄 N.
SECTION_PATTERN = re.compile(r'^(\d+)\.\s*$')

# TOC 회피
TOC_GUARD_LINES = 100

# 본편 종료 마커
END_MARKERS = ["*** END OF THE PROJECT GUTENBERG"]

# 부록 시작 마커 (Peoples and Countries)
APPENDIX_MARKERS = ["PEOPLES AND COUNTRIES", "Peoples and Countries"]


def find_essay_boundaries(lines):
    """에세이 마커 위치 (TOC 영역 회피)."""
    boundaries = []
    for i, line in enumerate(lines):
        if i < TOC_GUARD_LINES:
            continue
        m = ESSAY_PATTERN.match(line.strip())
        if m:
            essay_num = ESSAY_NUM[m.group(1)]
            boundaries.append((essay_num, i))
    return boundaries


def find_preface_start(lines, essay_first_line):
    """Preface 시작: TOC 이후 ~ 첫 essay 본문 이전 영역에서 첫 1. 줄."""
    for i in range(85, essay_first_line):
        m = SECTION_PATTERN.match(lines[i])
        if m and m.group(1) == '1':
            return i
    return None


def find_appendix_line(lines, search_from):
    """Peoples and Countries 부록 시작 위치 찾기."""
    for i in range(search_from, len(lines)):
        line = lines[i].strip()
        if any(m in line for m in APPENDIX_MARKERS):
            if len(line) < 60:
                return i
    return None


def find_end_line(lines, search_from):
    for i in range(search_from, len(lines)):
        if any(m in lines[i] for m in END_MARKERS):
            return i
    return len(lines)


def extract_sections_in_range(lines, start, end, essay_num):
    """주어진 범위에서 단락 추출."""
    positions = []
    for i in range(start, end):
        m = SECTION_PATTERN.match(lines[i])
        if m:
            positions.append((i, int(m.group(1))))
    
    chunks = []
    for idx, (line_idx, sec_num) in enumerate(positions):
        body_start = line_idx + 1
        if idx + 1 < len(positions):
            body_end = positions[idx + 1][0]
        else:
            body_end = end
        body = "".join(lines[body_start:body_end]).strip()
        
        chunks.append({
            "work": "GM",
            "essay": essay_num,  # 0 = preface, 1/2/3 = essays
            "aph_num": sec_num,
            "text_en": body,
            "line_start": line_idx + 1,
            "line_end": body_end,
            "char_count": len(body),
        })
    return chunks


def main():
    if not INPUT.exists():
        raise FileNotFoundError(f"입력 없음: {INPUT}")
    
    with INPUT.open(encoding="utf-8") as f:
        lines = f.readlines()
    
    boundaries = find_essay_boundaries(lines)
    print(f"에세이 마커 발견: {len(boundaries)}개")
    for num, start in boundaries:
        print(f"  Essay {num}: line {start + 1}")
    
    preface_start = find_preface_start(lines, boundaries[0][1]) if boundaries else None
    if preface_start is not None:
        print(f"  Preface: line {preface_start + 1}")
    
    # 종료 위치: 부록 또는 EOF
    last_essay_line = boundaries[-1][1] if boundaries else 0
    appendix_line = find_appendix_line(lines, last_essay_line)
    if appendix_line is not None:
        end_line = appendix_line
        print(f"부록 발견 (제외): line {appendix_line + 1}")
    else:
        end_line = find_end_line(lines, search_from=last_essay_line)
    print(f"본편 종료: line {end_line + 1}")
    
    all_chunks = []
    
    # Preface (essay 0)
    if preface_start is not None and boundaries:
        preface_chunks = extract_sections_in_range(
            lines, preface_start, boundaries[0][1], essay_num=0
        )
        all_chunks.extend(preface_chunks)
    
    # 각 에세이
    for idx, (essay_num, start) in enumerate(boundaries):
        if idx + 1 < len(boundaries):
            essay_end = boundaries[idx + 1][1]
        else:
            essay_end = end_line
        chunks = extract_sections_in_range(lines, start, essay_end, essay_num)
        all_chunks.extend(chunks)
    
    print(f"\n추출 청크: {len(all_chunks)}개")
    
    if all_chunks:
        by_essay = Counter(c["essay"] for c in all_chunks)
        for essay in sorted(by_essay):
            label = "Preface" if essay == 0 else f"Essay {essay}"
            essay_chunks = [c for c in all_chunks if c["essay"] == essay]
            nums = [c["aph_num"] for c in essay_chunks]
            print(f"  {label}: {by_essay[essay]}개 (#{min(nums)}~{max(nums)})")
        
        char_counts = [c["char_count"] for c in all_chunks]
        print(f"\n청크 길이: 평균 {sum(char_counts)//len(char_counts)}자, "
              f"최소 {min(char_counts)}, 최대 {max(char_counts)}")
    
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    
    print(f"\n✅ 저장: {OUTPUT}")


if __name__ == "__main__":
    main()