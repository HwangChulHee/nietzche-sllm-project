"""EH (Ecce Homo) 영어 청커.

- 메인 챕터 5개: PREFACE, WHY I AM SO WISE, WHY I AM SO CLEVER,
  WHY I WRITE SUCH EXCELLENT BOOKS, WHY I AM A FATALITY
- 챕터 안에서 번호가 리셋되면 sub_chapter 자동 분리
  (예: "Why I Write..." 안의 BT/UM/HAH/D/JW/TSZ/BGE/GM/TI/Wagner 회고)
- 청크 ID: (work, chapter, sub_chapter, aph_num)
"""
import json
import re
from pathlib import Path
from collections import Counter

INPUT = Path("v2_data/english_raw/ecce-homo.txt")
OUTPUT = Path("v2_data/english_chunks/eh.jsonl")

# 메인 챕터 헤더 (정확 매칭)
MAIN_CHAPTERS = [
    "PREFACE",
    "WHY I AM SO WISE",
    "WHY I AM SO CLEVER",
    "WHY I WRITE SUCH EXCELLENT BOOKS",
    "WHY I AM A FATALITY",
]

# TOC 가드
TOC_GUARD = 200

# 본편 종료 마커
END_MARKERS = [
    "EDITORIAL NOTE TO POETRY",
    "*** END OF THE PROJECT GUTENBERG",
]

# 아포리즘 번호: 단독 줄 N OR 인라인 N. Text
APH_NUM_RE = re.compile(r'^(\d+)(?:\.\s*|$)')


def find_main_chapters(lines):
    """메인 챕터 시작 위치 찾기 (TOC 이후)."""
    chapters = []
    for i, line in enumerate(lines):
        if i < TOC_GUARD:
            continue
        s = line.rstrip()
        if s in MAIN_CHAPTERS:
            chapters.append((i, s))
    return chapters


def find_end_line(lines, search_from):
    for i in range(search_from, len(lines)):
        if any(m in lines[i] for m in END_MARKERS):
            return i
    return len(lines)


def extract_aphorisms_with_subchapters(lines, ch_start, ch_end):
    """챕터 범위에서 아포리즘 추출. 번호 리셋 시 sub_chapter 분리."""
    positions = []
    for i in range(ch_start + 1, ch_end):
        s = lines[i].rstrip()
        m = APH_NUM_RE.match(s)
        if m:
            is_inline = '.' in s and len(s) > len(m.group(1)) + 1
            positions.append((i, int(m.group(1)), is_inline))
    
    # 번호 리셋 감지 → sub_chapter 증가
    sub_chapter = 0
    prev_num = 0
    items = []
    for line_idx, num, is_inline in positions:
        if num <= prev_num:
            sub_chapter += 1
        items.append((line_idx, num, is_inline, sub_chapter))
        prev_num = num
    
    aphorisms = []
    for idx, (line_idx, num, is_inline, sub_ch) in enumerate(items):
        body_start = line_idx if is_inline else line_idx + 1
        if idx + 1 < len(items):
            body_end = items[idx + 1][0]
        else:
            body_end = ch_end
        body = "".join(lines[body_start:body_end]).strip()
        aphorisms.append((num, sub_ch, body, line_idx, body_end))
    return aphorisms


def main():
    if not INPUT.exists():
        raise FileNotFoundError(f"입력 없음: {INPUT}")
    
    with INPUT.open(encoding="utf-8") as f:
        lines = f.readlines()
    
    chapters = find_main_chapters(lines)
    print(f"메인 챕터 발견: {len(chapters)}개")
    for idx, (ln, title) in enumerate(chapters, 1):
        print(f"  Ch {idx}: line {ln + 1} | {title}")
    
    if not chapters:
        raise RuntimeError("챕터 못 찾음")
    
    # 종료 위치
    last_ch_line = chapters[-1][0]
    end_line = find_end_line(lines, search_from=last_ch_line)
    print(f"본편 종료: line {end_line + 1}")
    
    all_chunks = []
    for ch_idx, (ch_line, ch_title) in enumerate(chapters, 1):
        next_ch_line = chapters[ch_idx][0] if ch_idx < len(chapters) else end_line
        aphorisms = extract_aphorisms_with_subchapters(lines, ch_line, next_ch_line)
        
        # 번호 없는 챕터 (예: PREFACE는 짧을 수 있음) → 챕터 전체를 1청크
        if not aphorisms:
            body = "".join(lines[ch_line + 1:next_ch_line]).strip()
            if body:
                aphorisms = [(1, 0, body, ch_line, next_ch_line)]
        
        for num, sub_ch, body, line_start, line_end in aphorisms:
            all_chunks.append({
                "work": "EH",
                "chapter": ch_idx,
                "chapter_title": ch_title,
                "sub_chapter": sub_ch,
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
            title = ch_chunks[0]["chapter_title"]
            sub_count = len(set(c["sub_chapter"] for c in ch_chunks))
            print(f"  Ch {ch} ({title[:40]}): {by_ch[ch]}개 (sub_chapter {sub_count}개)")
        
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