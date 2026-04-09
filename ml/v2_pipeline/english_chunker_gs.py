"""GS (The Joyful Wisdom) 영어 청커.

본편 1~383 아포리즘만 추출. 서문/시/부록은 스킵.
"""
import json
import re
from pathlib import Path

# 입출력 경로
INPUT = Path("v2_data/english_raw/the-joyful-wisdom.txt")
OUTPUT = Path("v2_data/english_chunks/gs.jsonl")

# 부 마커 (line 위치는 동적으로 찾음)
BOOK_MARKERS = [
    ("BOOK FIRST", 1),
    ("BOOK SECOND", 2),
    ("BOOK THIRD", 3),
    ("BOOK FOURTH", 4),
    ("BOOK FIFTH", 5),
]
END_MARKER = "APPENDIX"  # 본편 종료 신호

# 아포리즘 패턴: 가운데 정렬된 단독 N. 줄
APH_PATTERN = re.compile(r"^\s{10,}(\d+)\.\s*$")


def find_book_boundaries(lines):
    """BOOK 마커 위치 찾기. 반환: [(book_num, start_line), ...] + 종료 line."""
    boundaries = []
    end_line = len(lines)
    for i, line in enumerate(lines):
        stripped = line.strip()
        for marker, num in BOOK_MARKERS:
            if stripped == marker:
                boundaries.append((num, i))
        if stripped == END_MARKER:
            end_line = i
            break
    return boundaries, end_line


def book_for_line(line_idx, boundaries):
    """주어진 line이 어느 부에 속하는지."""
    current = None
    for book_num, start in boundaries:
        if line_idx >= start:
            current = book_num
        else:
            break
    return current


def extract_chunks(lines, boundaries, end_line):
    """본편 영역에서 아포리즘 청크 추출."""
    main_start = boundaries[0][1]  # BOOK FIRST 시작
    
    # 본편 범위 안의 모든 아포리즘 헤더 위치
    aph_positions = []
    for i in range(main_start, end_line):
        m = APH_PATTERN.match(lines[i])
        if m:
            aph_positions.append((i, int(m.group(1))))
    
    # 청크 생성
    chunks = []
    for idx, (line_idx, aph_num) in enumerate(aph_positions):
        # 본문 시작: 헤더 다음 줄
        body_start = line_idx + 1
        # 본문 끝: 다음 아포리즘 헤더 직전, 또는 본편 끝
        if idx + 1 < len(aph_positions):
            body_end = aph_positions[idx + 1][0]
        else:
            body_end = end_line
        
        body = "".join(lines[body_start:body_end]).strip()
        
        chunks.append({
            "work": "GS",
            "book": book_for_line(line_idx, boundaries),
            "aph_num": aph_num,
            "text_en": body,
            "line_start": line_idx + 1,  # 1-indexed
            "line_end": body_end,
            "char_count": len(body),
        })
    
    return chunks


def main():
    if not INPUT.exists():
        raise FileNotFoundError(f"입력 없음: {INPUT}")
    
    with INPUT.open(encoding="utf-8") as f:
        lines = f.readlines()
    
    boundaries, end_line = find_book_boundaries(lines)
    print(f"부 마커 발견: {len(boundaries)}개")
    for num, start in boundaries:
        print(f"  Book {num}: line {start + 1}")
    print(f"본편 종료: line {end_line + 1}")
    
    chunks = extract_chunks(lines, boundaries, end_line)
    print(f"\n추출 청크: {len(chunks)}개")
    
    # 검증
    aph_nums = [c["aph_num"] for c in chunks]
    print(f"번호 범위: {min(aph_nums)} ~ {max(aph_nums)}")
    print(f"중복: {len(aph_nums) - len(set(aph_nums))}개")
    
    # 본별 분포
    from collections import Counter
    by_book = Counter(c["book"] for c in chunks)
    for book in sorted(by_book):
        print(f"  Book {book}: {by_book[book]}개")
    
    # 통계
    char_counts = [c["char_count"] for c in chunks]
    print(f"\n청크 길이: 평균 {sum(char_counts) // len(char_counts)}자, "
          f"최소 {min(char_counts)}, 최대 {max(char_counts)}")
    
    # 출력
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    
    print(f"\n✅ 저장: {OUTPUT}")


if __name__ == "__main__":
    main()