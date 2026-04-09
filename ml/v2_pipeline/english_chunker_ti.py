"""TI (Twilight of the Idols) 영어 청커.

- 챕터 헤더: ALL CAPS 단독 줄 (curly quote 시작 허용)
- 아포리즘 번호: 단독 줄 N OR 인라인 N. Text (챕터마다 리셋)
- 번호 없는 챕터(예: The Hammer Speaketh): 챕터 전체를 1청크
- 청크 ID: (work, chapter_idx, aph_num)
- TI 본편만 (Antichrist, Eternal Recurrence 제외)
"""
import json
import re
from pathlib import Path
from collections import Counter

INPUT = Path("v2_data/english_raw/the-twilight-of-the-idols.txt")
OUTPUT = Path("v2_data/english_chunks/ti.jsonl")

# 본편 시작/종료 마커
BODY_START_MARKER = "MAXIMS AND MISSILES"
BODY_END_MARKER = "THE ANTICHRIST"

# TOC 가드: 첫 N줄의 마커는 무시
TOC_GUARD = 200

# 챕터 헤더: ALL CAPS, 따옴표로 시작 가능, 길이 5~80
CHAPTER_HEADER_RE = re.compile(r'^["\u201c]?[A-Z][A-Z0-9 ".“”\'’\-—!?]{4,80}$')

# 아포리즘 번호: 단독 줄 N OR 인라인 "N. Text"
APH_NUM_RE = re.compile(r'^(\d+)(?:\.\s+|$)')

# 챕터 헤더가 아닌 ALL CAPS 줄 제외 리스트
NON_CHAPTER_HEADERS = {
    "THE TWILIGHT OF THE IDOLS",
    "THE END.",
    "THE END",
    "THE HISTORY OF AN ERROR",  # Ch3의 부제
}


def find_body_range(lines):
    """본편 시작/종료 라인 찾기. TOC 영역 무시."""
    start, end = None, len(lines)
    for i, line in enumerate(lines):
        if i < TOC_GUARD:
            continue
        s = line.strip()
        if start is None and s == BODY_START_MARKER:
            start = i
        elif start is not None and s == BODY_END_MARKER:
            end = i
            break
    return start, end


def is_chapter_header(line_stripped):
    if line_stripped in NON_CHAPTER_HEADERS:
        return False
    if not CHAPTER_HEADER_RE.match(line_stripped):
        return False
    if len(line_stripped) < 5:
        return False
    return True


def find_chapters(lines, body_start, body_end):
    """본편 범위에서 챕터 헤더 위치 찾기."""
    chapters = []
    for i in range(body_start, body_end):
        s = lines[i].rstrip()
        if not is_chapter_header(s):
            continue
        # 헤더는 보통 빈 줄로 격리됨
        prev_blank = i == 0 or not lines[i - 1].strip()
        next_blank = i + 1 >= len(lines) or not lines[i + 1].strip()
        if prev_blank or next_blank:
            chapters.append((i, s))
    return chapters


def extract_aphorisms_in_chapter(lines, ch_start, ch_end):
    """챕터 범위에서 아포리즘 추출. 단독 번호와 인라인 둘 다 지원."""
    positions = []
    for i in range(ch_start + 1, ch_end):
        s = lines[i].rstrip()
        m = APH_NUM_RE.match(s)
        if m:
            # 인라인 여부: "N." 뒤에 텍스트가 있는가
            is_inline = '.' in s and len(s) > len(m.group(1)) + 1
            positions.append((i, int(m.group(1)), is_inline))
    
    aphorisms = []
    for idx, (line_idx, num, is_inline) in enumerate(positions):
        # 인라인이면 같은 줄부터, 단독이면 다음 줄부터
        body_start = line_idx if is_inline else line_idx + 1
        if idx + 1 < len(positions):
            body_end = positions[idx + 1][0]
        else:
            body_end = ch_end
        body = "".join(lines[body_start:body_end]).strip()
        aphorisms.append((num, body, line_idx, body_end))
    return aphorisms


def main():
    if not INPUT.exists():
        raise FileNotFoundError(f"입력 없음: {INPUT}")
    
    with INPUT.open(encoding="utf-8") as f:
        lines = f.readlines()
    
    body_start, body_end = find_body_range(lines)
    if body_start is None:
        raise RuntimeError("본편 시작 마커 못 찾음")
    print(f"본편 범위: line {body_start + 1} ~ {body_end + 1}")
    
    chapters = find_chapters(lines, body_start, body_end)
    print(f"\n챕터 발견: {len(chapters)}개")
    for idx, (ln, title) in enumerate(chapters, 1):
        print(f"  Ch {idx}: line {ln + 1} | {title}")
    
    all_chunks = []
    for ch_idx, (ch_line, ch_title) in enumerate(chapters, 1):
        next_ch_line = chapters[ch_idx][0] if ch_idx < len(chapters) else body_end
        aphorisms = extract_aphorisms_in_chapter(lines, ch_line, next_ch_line)
        
        # 번호 없는 챕터(예: Hammer Speaketh) → 챕터 전체를 1청크
        if not aphorisms:
            body = "".join(lines[ch_line + 1:next_ch_line]).strip()
            if body:
                aphorisms = [(1, body, ch_line, next_ch_line)]
        
        for num, body, line_start, line_end in aphorisms:
            all_chunks.append({
                "work": "TI",
                "chapter": ch_idx,
                "chapter_title": ch_title,
                "aph_num": num,
                "text_en": body,
                "line_start": line_start + 1,
                "line_end": line_end,
                "char_count": len(body),
            })
    
    print(f"\n추출 청크: {len(all_chunks)}개")
    
    if all_chunks:
        by_ch = Counter(c["chapter"] for c in all_chunks)
        for ch in sorted(by_ch):
            ch_chunks = [c for c in all_chunks if c["chapter"] == ch]
            nums = [c["aph_num"] for c in ch_chunks]
            title = ch_chunks[0]["chapter_title"]
            print(f"  Ch {ch} ({title[:45]}): {by_ch[ch]}개 (#{min(nums)}~{max(nums)})")
        
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