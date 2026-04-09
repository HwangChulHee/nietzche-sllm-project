"""BGE (Beyond Good and Evil) 영어 청커.

본편 296 아포리즘 추출. 패턴: ^N. Text... (인라인, 단독 줄 아님).
부 구조 9개 (Part One ~ Part Nine) 보존.
"""
import json
import re
from pathlib import Path
from collections import Counter

INPUT = Path("v2_data/english_raw/beyond-good-and-evil.txt")
OUTPUT = Path("v2_data/english_chunks/bge.jsonl")

# 실제 챕터: "CHAPTER I. PREJUDICES OF PHILOSOPHERS" (들여쓰기 없음, 점 + 제목)
# TOC는 "    CHAPTER I:    PREJUDICES..." (들여쓰기 + 콜론) — 자동 제외
PART_PATTERNS = [
    (re.compile(r'^CHAPTER\s+([IVX]+)\.\s+(.+)$'), 'roman'),
]

# 본편 종료 마커 (BGE는 "FROM THE HEIGHTS" 같은 후기 시 또는 END)
END_MARKERS = ["FROM THE HEIGHTS", "*** END"]

# 수정: 단독 줄 / em dash / 공백 + 텍스트 모두 매칭
APH_PATTERN = re.compile(r'^(\d+)\.(?:\s|--|$)')


ROMAN = {'I':1,'II':2,'III':3,'IV':4,'V':5,'VI':6,'VII':7,'VIII':8,'IX':9,'X':10}

def find_part_boundaries(lines):
    boundaries = []
    for i, line in enumerate(lines):
        # TOC 제외: 들여쓰기 없는 줄만
        if line.startswith(' ') or line.startswith('\t'):
            continue
        for pat, kind in PART_PATTERNS:
            m = pat.match(line)
            if m:
                roman = m.group(1)
                part_num = ROMAN.get(roman, len(boundaries) + 1)
                title = m.group(2).strip()
                boundaries.append((part_num, i, title))
                break
    return boundaries


def find_end_line(lines, search_from=0):
    """본편 종료 마커를 search_from 이후에서 찾기."""
    for i in range(search_from, len(lines)):
        if any(m in lines[i] for m in END_MARKERS):
            return i
    return len(lines)


def find_main_start(lines, boundaries):
    """본편 시작: 첫 부 마커 이후, 첫 아포리즘 #1이 나오는 위치."""
    if boundaries:
        return boundaries[0][1]
    # fallback: 첫 ^1. 패턴
    for i, line in enumerate(lines):
        if APH_PATTERN.match(line) and APH_PATTERN.match(line).group(1) == '1':
            return i
    return 0


def part_for_line(line_idx, boundaries):
    current = None
    for part_num, start, _ in boundaries:
        if line_idx >= start:
            current = part_num
        else:
            break
    return current


def extract_chunks(lines, boundaries, end_line):
    main_start = find_main_start(lines, boundaries)
    
    # 본편 범위에서 아포리즘 헤더 위치 찾기
    aph_positions = []
    for i in range(main_start, end_line):
        m = APH_PATTERN.match(lines[i])
        if m:
            aph_positions.append((i, int(m.group(1))))
    
    chunks = []
    for idx, (line_idx, aph_num) in enumerate(aph_positions):
        # 본문: 헤더 줄(인라인 텍스트 포함) ~ 다음 헤더 직전
        if idx + 1 < len(aph_positions):
            body_end = aph_positions[idx + 1][0]
        else:
            body_end = end_line
        
        body = "".join(lines[line_idx:body_end]).strip()
        
        chunks.append({
            "work": "BGE",
            "part": part_for_line(line_idx, boundaries),
            "aph_num": aph_num,
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
    
    boundaries = find_part_boundaries(lines)
    
    # 마지막 부 마커 이후에서 종료 마커 검색
    last_part_line = boundaries[-1][1] if boundaries else 0
    end_line = find_end_line(lines, search_from=last_part_line)
    
    print(f"부 마커 발견: {len(boundaries)}개")
    for num, start, text in boundaries:
        print(f"  Part {num}: line {start + 1} ({text})")
    print(f"본편 종료: line {end_line + 1}")
    
    chunks = extract_chunks(lines, boundaries, end_line)
    print(f"\n추출 청크: {len(chunks)}개")
    
    if chunks:
        aph_nums = [c["aph_num"] for c in chunks]
        print(f"번호 범위: {min(aph_nums)} ~ {max(aph_nums)}")
        print(f"중복: {len(aph_nums) - len(set(aph_nums))}개")
        
        # 번호 빠짐 검사
        expected = set(range(min(aph_nums), max(aph_nums) + 1))
        missing = sorted(expected - set(aph_nums))
        if missing:
            print(f"빠진 번호: {missing[:20]}{'...' if len(missing) > 20 else ''}")
        
        by_part = Counter(c["part"] for c in chunks)
        for part in sorted(by_part, key=lambda x: (x is None, x)):
            print(f"  Part {part}: {by_part[part]}개")
        
        char_counts = [c["char_count"] for c in chunks]
        print(f"\n청크 길이: 평균 {sum(char_counts)//len(char_counts)}자, "
              f"최소 {min(char_counts)}, 최대 {max(char_counts)}")
    
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    
    print(f"\n✅ 저장: {OUTPUT}")


if __name__ == "__main__":
    main()