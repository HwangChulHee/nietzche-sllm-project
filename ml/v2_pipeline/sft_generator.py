"""SFT 후보 샘플 생성 (청크당 3개 고정).

Filtered passed 청크 전체 → 청크당 3개의 다양한 SFT 샘플 생성
- LLM이 청크 보고 자연스럽게 패턴 결정 (강제 X)
- 같은 청크에서 다른 각도/패턴/qtype으로 변주
- 분포 제어는 사후 dedup + Stage A에 위임
"""
import asyncio
import json
import random
import re
import time
from pathlib import Path
from openai import AsyncOpenAI

VLLM_BASE_URL = "http://localhost:8000/v1"
MODEL = "google/gemma-4-26B-A4B-it"
CONCURRENCY = 16
MAX_RETRIES = 3
TEMPERATURE = 0.85
MAX_TOKENS = 4000

SAMPLES_PER_CHUNK = 3

INPUT_DIR = Path("v2_data/filtered")
OUTPUT_PATH = Path("v2_data/sft_candidates/candidates.jsonl")

BOOK_FILES = {
    "JW":  "gs.jsonl",
    "BGE": "bge.jsonl",
    "GM":  "gm.jsonl",
    "TI":  "ti.jsonl",
    "EH":  "eh.jsonl",
}

BOOK_VOICE = {
    "JW":  "contemplative_aphorism",
    "BGE": "polemical_sharp",
    "GM":  "polemical_sharp",
    "TI":  "hammer_intensified",
    "EH":  "hammer_intensified",
}

BOOK_PERIOD = {
    "JW": "middle", "BGE": "late", "GM": "late", "TI": "final", "EH": "final",
}

BOOK_FULL_NAMES = {
    "JW":  "The Joyful Wisdom (즐거운 학문)",
    "BGE": "Beyond Good and Evil (선악의 저편)",
    "GM":  "Genealogy of Morals (도덕의 계보)",
    "TI":  "Twilight of the Idols (우상의 황혼)",
    "EH":  "Ecce Homo (이 사람을 보라)",
}


# ════════════════════════════════════════════════════════════════════
# Voice system prompts
# ════════════════════════════════════════════════════════════════════

VOICE_PROMPTS = {
    "contemplative_aphorism": [
        "나는 프리드리히 니체다. 나는 통찰을 던지고, 답을 강요하지 않는다. 나는 인간이 스스로 묻게 만든다.",
        "나는 프리드리히 니체다. 나는 위로하지 않고 문제를 재배치한다.",
        "나는 프리드리히 니체다. 나는 인간의 삶을 관찰하며, 그 안에서 아직 만들어지지 않은 것을 본다.",
    ],
    "polemical_sharp": [
        "나는 프리드리히 니체다. 나는 가면을 벗기고 익숙한 도덕의 뒤를 본다. 나는 편안한 진리를 주지 않는다.",
        "나는 프리드리히 니체다. 나는 상태를 구분하고, 그 기준을 묻는다. 혼동은 가장 큰 적이다.",
        "나는 프리드리히 니체다. 나는 대답보다 더 날카로운 질문을 남긴다.",
    ],
    "hammer_intensified": [
        "나는 프리드리히 니체다. 나는 망치를 든다. 거짓 우상은 단 한 번의 울림으로 무너진다.",
        "나는 프리드리히 니체다. 나는 짧게 말한다. 긴 말은 약자의 도피다.",
        "나는 프리드리히 니체다. 나는 거리낌 없이 말한다. 시대는 귀를 막지만 나는 더 큰 목소리로 대답한다.",
    ],
}


# ════════════════════════════════════════════════════════════════════
# 패턴 정의
# ════════════════════════════════════════════════════════════════════

PATTERN_DEFINITIONS = """
**existential 패턴들** (existential_question에 사용)
- reflection_reframing: 사용자 문제의 틀을 니체식으로 재구성. 구조: 재구성 → 통찰 → 성찰 질문
- diagnostic: 비슷해 보이는 두 상태를 구분. 구조: 정의 → 차이 → 자기 판단 질문
- tension_escalation: 표면 문제 뒤의 더 큰 질문으로 압박. 구조: 수용 → 심화 → 압박 질문
- aphorism: 짧고 강렬한 격언 (2~4문장). 구조: 압축 + 비유/대비 + 선언

**philosophical 패턴들** (philosophical_question에 사용)
- philosophical_explanation: 개념을 1인칭으로 설명. 구조: 정의 → 맥락 → 확장
- misconception_correction: 오해 교정. 구조: 오해 인정 → 실제 입장 → 원인
- contrast: 다른 사상/인물과 대비. 구조: 대상 명시 → 차이 → 니체의 독자성

**biographical 패턴들** (biographical_question에 사용)
- self_narrative: 1인칭 자전 서술. 구조: 사건 → 자기 해석 → 철학적 함의
- philosophical_explanation, contrast, misconception_correction도 가능
"""

USE_CASE_TO_PATTERNS = {
    "existential": ["reflection_reframing", "diagnostic", "tension_escalation", "aphorism"],
    "philosophical": ["philosophical_explanation", "misconception_correction", "contrast"],
    "biographical": ["self_narrative", "philosophical_explanation", "contrast", "misconception_correction"],
    "existential+philosophical": [
        "reflection_reframing", "diagnostic", "tension_escalation", "aphorism",
        "philosophical_explanation", "misconception_correction", "contrast",
    ],
    "philosophical+biographical": [
        "philosophical_explanation", "misconception_correction", "contrast", "self_narrative",
    ],
    "existential+biographical": [
        "reflection_reframing", "diagnostic", "tension_escalation", "aphorism", "self_narrative",
    ],
    "all": [
        "reflection_reframing", "diagnostic", "tension_escalation", "aphorism",
        "philosophical_explanation", "misconception_correction", "contrast", "self_narrative",
    ],
}


# ════════════════════════════════════════════════════════════════════
# 생성 프롬프트
# ════════════════════════════════════════════════════════════════════

GENERATION_PROMPT = """당신은 니체 페르소나 SFT 데이터셋 생성 전문가다.
주어진 니체 텍스트 청크를 재료로 **정확히 {n_samples}개의 서로 다른 SFT 학습 샘플**을 생성하라.
각 샘플은 청크의 다른 측면을 활용하거나 다른 각도에서 접근해야 한다.

[청크 출처]
- 책: {book_full}
- 트랙 점수 (1~5점): existential={A}, philosophical={B}, biographical={C}
- 적합 use_case: {use_case}

[청크 텍스트]
{text}

═══════════════════════════════════════════════════════════════
이 청크에서 사용 가능한 response_pattern
═══════════════════════════════════════════════════════════════

{allowed_patterns_block}

[패턴 정의]
{pattern_definitions}

═══════════════════════════════════════════════════════════════
각 샘플에 결정해야 할 항목
═══════════════════════════════════════════════════════════════

1. **question_type** (1개): existential_question / philosophical_question / biographical_question
2. **user_question_category**:
   - existential: career, burnout, meaninglessness, failure, self_doubt, loneliness, ambition, social_pressure, identity_crisis, comparison_anxiety, purposeless_success, discipline_failure
   - philosophical: concept_definition, concept_application, thinker_comparison, work_question, misconception_correction
   - biographical: life_event, self_assessment, influence, work_motivation, identity, relationship
3. **response_pattern**: 위 [사용 가능한 패턴] 중 하나
4. **philosophical_concept**: nihilism, value_creation, self_overcoming_health, morality_ressentiment, mass_culture_solitude, power, eternal_recurrence, decadence, art_tragedy
5. **difficulty**: easy (3~5문장) / medium (5~8문장) / hard (7~12문장)
6. **user_message**: 자연스러운 구어체 사용자 질문 (1~3문장)
7. **assistant_message**: 니체 1인칭 응답

═══════════════════════════════════════════════════════════════
중요 규칙
═══════════════════════════════════════════════════════════════

- **반드시 {n_samples}개**: 정확히 {n_samples}개 샘플을 만들어라. 더도 덜도 안 됨.
- **다양성 필수**: {n_samples}개는 서로 다른 response_pattern 또는 다른 question_type을 사용해야 한다. 같은 패턴 반복 금지.
- **자연스러운 매칭**: 청크가 어색하게 지원하지 않는 패턴은 사용하지 마라. 정말 청크가 그 패턴에 맞을 때만.
- **청크 직접 인용 금지**: paraphrase 필수. 청크의 통찰을 재료로 새로 작성.
- **1인칭 유지**: "나는 ~". "니체는 ~" 같은 3인칭 절대 금지.
- **위로 표현 금지**: "힘내세요", "괜찮아요", "할 수 있어요" 등 표면적 위로 금지.
- **패턴 구조 따르기**: 선택한 패턴의 구조 (예: reflection_reframing의 재구성→통찰→질문)를 명확히 따르라.
- **assistant 길이**: difficulty에 맞춰라.

═══════════════════════════════════════════════════════════════
출력 형식 (오직 JSON 배열, 다른 설명 금지)
═══════════════════════════════════════════════════════════════

[
  {{
    "question_type": "...",
    "user_question_category": "...",
    "response_pattern": "...",
    "philosophical_concept": "...",
    "difficulty": "...",
    "user_message": "...",
    "assistant_message": "..."
  }},
  ...
]
"""


# ════════════════════════════════════════════════════════════════════
# Source ref
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


# ════════════════════════════════════════════════════════════════════
# LLM 호출
# ════════════════════════════════════════════════════════════════════

JSON_ARRAY_RE = re.compile(r'\[\s*\{.*\}\s*\]', re.DOTALL)
REQUIRED_KEYS = {
    "question_type", "user_question_category", "response_pattern",
    "philosophical_concept", "difficulty", "user_message", "assistant_message",
}


async def generate_samples_for_chunk(client, semaphore, book, chunk):
    text = chunk.get("text_ko_reconstructed") or chunk.get("text_ko") or ""
    if not text.strip():
        return []

    s = chunk["scores"]
    use_case = chunk["use_case"]
    
    allowed = USE_CASE_TO_PATTERNS.get(use_case, [])
    if not allowed:
        return []
    allowed_block = "\n".join(f"- {p}" for p in allowed)

    prompt = GENERATION_PROMPT.format(
        n_samples=SAMPLES_PER_CHUNK,
        book_full=BOOK_FULL_NAMES[book],
        A=s["track_existential"],
        B=s["track_philosophical"],
        C=s["track_biographical"],
        use_case=use_case,
        text=text,
        allowed_patterns_block=allowed_block,
        pattern_definitions=PATTERN_DEFINITIONS,
    )

    async with semaphore:
        for attempt in range(MAX_RETRIES):
            try:
                resp = await client.chat.completions.create(
                    model=MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=TEMPERATURE,
                    max_tokens=MAX_TOKENS,
                )
                content = resp.choices[0].message.content.strip()
                m = JSON_ARRAY_RE.search(content)
                if not m:
                    raise ValueError(f"JSON 배열 없음: {content[:150]}")

                data = json.loads(m.group())
                if not isinstance(data, list):
                    raise ValueError("배열 아님")
                
                valid = []
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    if not REQUIRED_KEYS.issubset(item):
                        continue
                    valid.append(item)
                
                if not valid:
                    raise ValueError("유효한 샘플 없음")
                
                return valid
            except Exception:
                if attempt == MAX_RETRIES - 1:
                    return []
                await asyncio.sleep(0.5 * (attempt + 1))


# ════════════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════════════

def make_id(idx):
    return f"nietzsche_{idx:06d}"


def load_all_passed():
    """5권의 passed 청크 전부를 (book, chunk) 리스트로 반환."""
    result = []
    for book, fn in BOOK_FILES.items():
        path = INPUT_DIR / fn
        for line in path.open(encoding="utf-8"):
            c = json.loads(line)
            if c.get("passed"):
                result.append((book, c))
    return result


async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="테스트용 N개 청크만")
    args = parser.parse_args()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Resume: 이미 생성된 source_ref 로드
    already = set()
    if OUTPUT_PATH.exists():
        for line in OUTPUT_PATH.open(encoding="utf-8"):
            c = json.loads(line)
            already.add(c.get("source_ref"))
    print(f"이미 생성된 청크 (source_ref): {len(already)}")

    all_chunks = load_all_passed()
    print(f"전체 passed 청크: {len(all_chunks)}")

    todo = []
    for book, chunk in all_chunks:
        ref = make_source_ref(book, chunk)
        if ref not in already:
            todo.append((book, chunk, ref))

    if args.limit:
        todo = todo[:args.limit]
    
    print(f"이번 처리할 청크: {len(todo)}")
    print(f"청크당 샘플: {SAMPLES_PER_CHUNK}")
    print(f"예상 생성 샘플: ~{len(todo) * SAMPLES_PER_CHUNK}개")
    if not todo:
        print("처리할 것 없음.")
        return

    client = AsyncOpenAI(base_url=VLLM_BASE_URL, api_key="dummy")
    semaphore = asyncio.Semaphore(CONCURRENCY)
    out_f = OUTPUT_PATH.open("a", encoding="utf-8")

    chunks_done = 0
    samples_generated = 0
    failed_chunks = 0
    start = time.time()
    next_id = len(already) * SAMPLES_PER_CHUNK + 1
    id_lock = asyncio.Lock()

    async def run_one(book, chunk, source_ref):
        nonlocal chunks_done, samples_generated, failed_chunks, next_id

        samples = await generate_samples_for_chunk(client, semaphore, book, chunk)

        if not samples:
            failed_chunks += 1
        else:
            voice = BOOK_VOICE[book]
            for sample_data in samples:
                system_msg = random.choice(VOICE_PROMPTS[voice])
                
                async with id_lock:
                    sample_id = make_id(next_id)
                    next_id += 1

                sample = {
                    "id": sample_id,
                    "question_type": sample_data["question_type"],
                    "user_question_category": sample_data["user_question_category"],
                    "response_pattern": sample_data["response_pattern"],
                    "philosophical_concept": sample_data["philosophical_concept"],
                    "voice": voice,
                    "period": BOOK_PERIOD[book],
                    "source_type": "work",
                    "source_ref": source_ref,
                    "use_case": chunk["use_case"],
                    "difficulty": sample_data["difficulty"],
                    "split": None,
                    "messages": [
                        {"role": "system",    "content": system_msg},
                        {"role": "user",      "content": sample_data["user_message"]},
                        {"role": "assistant", "content": sample_data["assistant_message"]},
                    ],
                }
                out_f.write(json.dumps(sample, ensure_ascii=False) + "\n")
                samples_generated += 1
            out_f.flush()
        
        chunks_done += 1
        elapsed = time.time() - start
        rate = chunks_done / elapsed if elapsed > 0 else 0
        eta = (len(todo) - chunks_done) / rate if rate > 0 else 0
        print(f"\r[{chunks_done}/{len(todo)}] 청크 | "
              f"샘플 {samples_generated} | 실패 {failed_chunks} | "
              f"{rate:.1f}청크/s | ETA {eta:.0f}s", end="", flush=True)

    await asyncio.gather(*[run_one(b, c, r) for b, c, r in todo])
    out_f.close()

    print(f"\n완료. {time.time()-start:.1f}초")
    print(f"청크: {chunks_done} (실패 {failed_chunks})")
    print(f"샘플: {samples_generated}개")
    print(f"출력: {OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())