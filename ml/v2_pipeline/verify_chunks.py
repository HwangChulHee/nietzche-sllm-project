"""5권 영어 청크 검증."""
import json
from pathlib import Path
from collections import Counter

CHUNKS_DIR = Path("v2_data/english_chunks")

BOOKS = {
    "JW": {"file": "gs.jsonl", "expected_total": 383},  # GS 파일명 그대로
    "BGE": {"file": "bge.jsonl", "expected_total": 296},
    "GM": {"file": "gm.jsonl", "expected_total": None},  # 가변
    "TI": {"file": "ti.jsonl", "expected_total": None},
    "EH": {"file": "eh.jsonl", "expected_total": None},
}


def load(path):
    return [json.loads(l) for l in path.open(encoding="utf-8")]


def check_book(work, info):
    print(f"\n{'='*70}")
    print(f"  {work}")
    print('='*70)
    
    path = CHUNKS_DIR / info["file"]
    if not path.exists():
        print(f"  ❌ 파일 없음: {path}")
        return
    
    chunks = load(path)
    print(f"총 청크: {len(chunks)}")
    
    # 1. char_count 통계
    char_counts = [c["char_count"] for c in chunks]
    print(f"길이: 평균 {sum(char_counts)//len(char_counts)}자, "
          f"최소 {min(char_counts)}, 최대 {max(char_counts)}")
    
    # 2. 의심스러운 짧은 청크 (<100자)
    short = [c for c in chunks if c["char_count"] < 100]
    print(f"\n짧은 청크 (<100자): {len(short)}개")
    for c in short[:5]:
        loc = f"aph #{c['aph_num']}"
        if "chapter" in c:
            loc += f" ch{c['chapter']}"
        if "essay" in c:
            loc += f" essay{c['essay']}"
        if "sub_chapter" in c:
            loc += f" sub{c['sub_chapter']}"
        if "part" in c:
            loc += f" part{c['part']}"
        text = c["text_en"].replace("\n", " ")[:80]
        print(f"  {loc} ({c['char_count']}자): {text}")
    
    # 3. 의심스러운 긴 청크 (top 3)
    longest = sorted(chunks, key=lambda c: -c["char_count"])[:3]
    print(f"\n가장 긴 청크 top 3:")
    for c in longest:
        loc = f"aph #{c['aph_num']}"
        if "chapter" in c:
            loc += f" ch{c['chapter']}"
        if "essay" in c:
            loc += f" essay{c['essay']}"
        if "sub_chapter" in c:
            loc += f" sub{c['sub_chapter']}"
        text_start = c["text_en"][:80].replace("\n", " ")
        text_end = c["text_en"][-80:].replace("\n", " ")
        print(f"  {loc} ({c['char_count']}자)")
        print(f"    시작: {text_start}")
        print(f"    끝:   ...{text_end}")
    
    # 4. 첫 청크 + 마지막 청크 미리보기
    print(f"\n첫 청크:")
    print(f"  {chunks[0]['text_en'][:200]}")
    print(f"\n마지막 청크:")
    print(f"  {chunks[-1]['text_en'][:200]}")
    
    # 5. 빈 청크 / 공백만 청크
    empty = [c for c in chunks if not c["text_en"].strip()]
    if empty:
        print(f"\n⚠️  빈 청크: {len(empty)}개")
    
    # 6. 중복 (text_en 기준)
    text_counter = Counter(c["text_en"][:200] for c in chunks)
    dups = [(t, n) for t, n in text_counter.items() if n > 1]
    if dups:
        print(f"\n⚠️  중복 의심: {len(dups)}개")
        for t, n in dups[:3]:
            print(f"  ({n}회) {t[:80]}")


def main():
    for work, info in BOOKS.items():
        check_book(work, info)
    
    # 전체 합
    print(f"\n{'='*70}")
    print("  전체 요약")
    print('='*70)
    total = 0
    for work, info in BOOKS.items():
        path = CHUNKS_DIR / info["file"]
        if path.exists():
            n = len(load(path))
            total += n
            print(f"  {work}: {n}")
    print(f"  합: {total}")


if __name__ == "__main__":
    main()