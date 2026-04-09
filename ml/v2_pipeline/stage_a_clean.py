"""Stage A — Clean: enum 정규화 + Hygiene 자동 검사.

입력: v2_data/sft_candidates/candidates.jsonl
출력: v2_data/sft_candidates/cleaned.jsonl
     v2_data/sft_candidates/cleaned_report.json (폐기 통계)
"""
import json
import re
from collections import Counter
from pathlib import Path

INPUT = Path("v2_data/sft_candidates/candidates.jsonl")
OUTPUT = Path("v2_data/sft_candidates/cleaned.jsonl")
REPORT = Path("v2_data/sft_candidates/cleaned_report.json")
CHUNKS_DIR = Path("v2_data/filtered")

BOOK_FILES = {
    "JW":  "gs.jsonl",
    "BGE": "bge.jsonl",
    "GM":  "gm.jsonl",
    "TI":  "ti.jsonl",
    "EH":  "eh.jsonl",
}


# ════════════════════════════════════════════════════════════════════
# Enum 정규화
# ════════════════════════════════════════════════════════════════════

VALID_PATTERNS = {
    "reflection_reframing", "diagnostic", "tension_escalation", "aphorism",
    "philosophical_explanation", "misconception_correction", "contrast",
    "self_narrative", "safe_redirect",
}

PATTERN_FIXES = {
    "reflection_refframing": "reflection_reframing",
    "reflection-reframing": "reflection_reframing",
}

VALID_CONCEPTS = {
    "nihilism", "value_creation", "self_overcoming_health",
    "morality_ressentiment", "mass_culture_solitude", "power",
    "eternal_recurrence", "decadence", "art_tragedy",
}

CONCEPT_FIXES = {
    "self-overcoming-health": "self_overcoming_health",
    "self_overcoming": "self_overcoming_health",
    "value-creation": "value_creation",
    "morality-ressentiment": "morality_ressentiment",
    "mass-culture-solitude": "mass_culture_solitude",
    "eternal-recurrence": "eternal_recurrence",
    "art-tragedy": "art_tragedy",
}

VALID_QTYPES = {"existential_question", "philosophical_question", "biographical_question"}

VALID_DIFFICULTIES = {"easy", "medium", "hard"}


def normalize_enums(sample):
    """Enum 필드 정규화. 교정 가능하면 교정, 불가능하면 None 반환."""
    issues = []
    
    p = sample.get("response_pattern", "")
    if p in PATTERN_FIXES:
        sample["response_pattern"] = PATTERN_FIXES[p]
        issues.append(f"pattern_fixed:{p}→{PATTERN_FIXES[p]}")
    elif p not in VALID_PATTERNS:
        return None, f"invalid_pattern:{p}"
    
    c = sample.get("philosophical_concept", "")
    if c in CONCEPT_FIXES:
        sample["philosophical_concept"] = CONCEPT_FIXES[c]
        issues.append(f"concept_fixed:{c}→{CONCEPT_FIXES[c]}")
    elif c not in VALID_CONCEPTS:
        return None, f"invalid_concept:{c}"
    
    if sample.get("question_type") not in VALID_QTYPES:
        return None, f"invalid_qtype:{sample.get('question_type')}"
    
    if sample.get("difficulty") not in VALID_DIFFICULTIES:
        return None, f"invalid_difficulty:{sample.get('difficulty')}"
    
    return sample, ",".join(issues) if issues else None


# ════════════════════════════════════════════════════════════════════
# Hygiene: 표절 검사 (15-char overlap with source chunk)
# ════════════════════════════════════════════════════════════════════

PLAGIARISM_NGRAM = 15  # 한국어 15자 (대략 영어 5-단어 분량)


def strip_markdown(text):
    """*italic*, _emphasis_, **bold** 등 마크다운 기호 제거."""
    text = re.sub(r'\*+([^*]+)\*+', r'\1', text)
    text = re.sub(r'_+([^_]+)_+', r'\1', text)
    return text


def make_ngram_set(text, n=PLAGIARISM_NGRAM):
    """텍스트에서 길이 n의 연속 부분문자열 집합."""
    text = strip_markdown(text)
    text = re.sub(r'\s+', '', text)  # 공백 제거 (한국어는 공백 무시)
    if len(text) < n:
        return set()
    return {text[i:i+n] for i in range(len(text) - n + 1)}


def check_plagiarism(assistant_text, chunk_text):
    """assistant 응답이 청크와 15-char 이상 일치하는 부분이 있는지."""
    a = make_ngram_set(assistant_text)
    c = make_ngram_set(chunk_text)
    return bool(a & c)


# ════════════════════════════════════════════════════════════════════
# Hygiene: 위로 표현
# ════════════════════════════════════════════════════════════════════

COMFORT_PATTERNS = [
    r"힘내",
    r"괜찮(아|을|습니다)",
    r"할 수 있어",
    r"걱정.*마(세요|십시오)",
    r"이해해(요|줍니다)",
    r"마음.*알아(요|줘)",
    r"모두가.*경험",
    r"누구나.*겪",
]
COMFORT_RE = re.compile("|".join(COMFORT_PATTERNS))


def check_comfort(text):
    """위로 표현 발견 시 True."""
    return bool(COMFORT_RE.search(text))


# ════════════════════════════════════════════════════════════════════
# Hygiene: 길이 (difficulty 기준)
# ════════════════════════════════════════════════════════════════════

DIFFICULTY_RANGES = {
    "easy":   (3, 5),
    "medium": (5, 8),
    "hard":   (7, 12),
}

# 한국어 문장 종결: 다. 까. !? 등
SENTENCE_END_RE = re.compile(r'[.!?](?:\s|$)|(?<=다)\.|(?<=까)\?')


def count_sentences(text):
    text = strip_markdown(text).strip()
    if not text:
        return 0
    # 종결 부호 기준으로 분할
    parts = re.split(r'[.!?]+(?:\s|$)', text)
    return len([p for p in parts if p.strip()])


def check_length(text, difficulty, tolerance=2):
    """difficulty 범위 ± tolerance 안인가."""
    lo, hi = DIFFICULTY_RANGES.get(difficulty, (3, 12))
    n = count_sentences(text)
    return (lo - tolerance) <= n <= (hi + tolerance), n


# ════════════════════════════════════════════════════════════════════
# 청크 텍스트 로드 (source_ref → text 매핑)
# ════════════════════════════════════════════════════════════════════

def make_source_ref(book, chunk):
    n = chunk.get("aph_num", 0)
    if book == "GM":
        return f"GM_e{chunk.get('essay', 0)}_s{n}"
    if book == "TI":
        return f"TI_c{chunk.get('chapter', 0)}_s{n}"
    if book == "EH":
        c = chunk.get("chapter", 0)
        sub = chunk.get("sub_chapter", 0)
        return f"EH_c{c}_sub{sub}_s{n}" if sub else f"EH_c{c}_s{n}"
    if book == "BGE":
        return f"BGE_p{chunk.get('part', 0)}_s{n}"
    return f"JW_s{n}"


def load_chunk_texts():
    """source_ref → 청크 한국어 텍스트 매핑 빌드."""
    mapping = {}
    for book, fn in BOOK_FILES.items():
        path = CHUNKS_DIR / fn
        for line in path.open(encoding="utf-8"):
            c = json.loads(line)
            ref = make_source_ref(book, c)
            mapping[ref] = c.get("text_ko_reconstructed") or c.get("text_ko") or ""
    return mapping


# ════════════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════════════

def main():
    print("청크 텍스트 로드 중...")
    chunk_texts = load_chunk_texts()
    print(f"  {len(chunk_texts)}개 청크")
    
    samples = [json.loads(l) for l in INPUT.open(encoding="utf-8")]
    print(f"\n입력 샘플: {len(samples)}개")
    
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    out_f = OUTPUT.open("w", encoding="utf-8")
    
    stats = Counter()
    fix_log = Counter()
    kept = 0
    
    for sample in samples:
        # Step 1: enum 정규화
        normalized, fix_info = normalize_enums(dict(sample))
        if normalized is None:
            stats[f"discard_{fix_info}"] += 1
            stats["discard_total"] += 1
            continue
        if fix_info:
            fix_log[fix_info] += 1
        
        # Step 2: assistant 추출
        assistant = ""
        for m in normalized["messages"]:
            if m["role"] == "assistant":
                assistant = m["content"]
                break
        
        if not assistant.strip():
            stats["discard_empty_assistant"] += 1
            stats["discard_total"] += 1
            continue
        
        # Step 3: hygiene — 표절
        chunk_text = chunk_texts.get(normalized["source_ref"], "")
        if chunk_text and check_plagiarism(assistant, chunk_text):
            stats["discard_plagiarism"] += 1
            stats["discard_total"] += 1
            continue
        
        # Step 4: hygiene — 위로
        if check_comfort(assistant):
            stats["discard_comfort"] += 1
            stats["discard_total"] += 1
            continue
        
        # Step 5: hygiene — 길이
        ok, n_sent = check_length(assistant, normalized["difficulty"])
        if not ok:
            stats["discard_length"] += 1
            stats["discard_total"] += 1
            continue
        
        # 통과
        out_f.write(json.dumps(normalized, ensure_ascii=False) + "\n")
        kept += 1
    
    out_f.close()
    
    # 리포트
    discard_total = stats["discard_total"]
    print(f"\n{'='*60}")
    print(f"  Stage A Clean 결과")
    print(f"{'='*60}")
    print(f"입력:    {len(samples)}")
    print(f"통과:    {kept} ({kept/len(samples)*100:.1f}%)")
    print(f"폐기:    {discard_total} ({discard_total/len(samples)*100:.1f}%)")
    print()
    print("폐기 사유별:")
    for k, v in sorted(stats.items()):
        if k.startswith("discard_") and k != "discard_total":
            print(f"  {k.replace('discard_', ''):30} {v}")
    
    if fix_log:
        print()
        print("자동 교정:")
        for k, v in fix_log.most_common():
            print(f"  {k}: {v}")
    
    print(f"\n출력: {OUTPUT}")
    
    REPORT.write_text(json.dumps({
        "input": len(samples),
        "kept": kept,
        "discarded": discard_total,
        "discard_breakdown": {k: v for k, v in stats.items() if k != "discard_total"},
        "fixes": dict(fix_log),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"리포트: {REPORT}")


if __name__ == "__main__":
    main()