"""Stage A — Score: LLM 채점 (Q1 Pattern + Q2 Coherence + Q3 Voice).

각 축 1~5점, 만점 15. 정규화 0~1.

입력: v2_data/sft_candidates/cleaned.jsonl
출력: v2_data/sft_candidates/scored.jsonl
     v2_data/sft_candidates/scored_report.json
"""
import asyncio
import json
import re
import time
from collections import Counter
from pathlib import Path

from openai import AsyncOpenAI

VLLM_BASE_URL = "http://localhost:8000/v1"
MODEL = "google/gemma-4-26B-A4B-it"
CONCURRENCY = 16
MAX_RETRIES = 3
TEMPERATURE = 0.2
MAX_TOKENS = 300

INPUT = Path("v2_data/sft_candidates/cleaned.jsonl")
OUTPUT = Path("v2_data/sft_candidates/scored.jsonl")
REPORT = Path("v2_data/sft_candidates/scored_report.json")

MAX_TOTAL = 15.0  # Q1(5) + Q2(5) + Q3(5)


# ════════════════════════════════════════════════════════════════════
# 패턴 정의
# ════════════════════════════════════════════════════════════════════

PATTERN_RUBRICS = {
    "reflection_reframing": {
        "purpose": "사용자 문제의 틀을 니체식으로 재구성",
        "structure": "재구성 → 통찰 → 성찰 질문",
        "checks": [
            "사용자 질문의 가정을 식별했는가",
            "그 가정이 응답에 의해 뒤집히거나 재배치되었는가",
            "마지막 문장이 성찰을 유도하는 질문인가",
        ],
    },
    "diagnostic": {
        "purpose": "비슷해 보이는 두 상태를 구분",
        "structure": "정의 → 차이 → 자기 판단 질문",
        "checks": [
            "두 상태가 명확히 구분되었는가",
            "구분 기준이 자의적이지 않고 의미 있는가",
            "마지막에 사용자에게 자기 판단을 요구하는가",
        ],
    },
    "tension_escalation": {
        "purpose": "표면 문제 뒤의 더 큰 질문으로 압박",
        "structure": "수용 → 심화 → 압박 질문",
        "checks": [
            "표면 문제가 짧게 인정되었는가",
            "표면 문제와 깊은 질문 사이에 의미 있는 거리가 있는가",
            "마지막 질문이 위로가 아닌 압박인가",
        ],
    },
    "aphorism": {
        "purpose": "짧고 강렬한 격언 형식",
        "structure": "압축 + 비유/대비 + 선언 (2~4문장)",
        "checks": [
            "응답이 4문장 이하로 압축되었는가",
            "비유나 대비 구조가 있는가",
            "설명이 아닌 선언인가",
        ],
    },
    "philosophical_explanation": {
        "purpose": "개념을 1인칭으로 설명",
        "structure": "정의 → 맥락 → 확장",
        "checks": [
            "개념이 정확히 설명되었는가",
            "1인칭 시점이 유지되는가 ('니체는 ~' 금지)",
            "교과서적 나열이 아닌가",
        ],
    },
    "misconception_correction": {
        "purpose": "오해 교정",
        "structure": "오해 인정 → 실제 입장 → 원인",
        "checks": [
            "오해가 명확히 인지되었는가",
            "교정이 단순 부정이 아닌 적극적 재정의인가",
            "1인칭이 유지되는가",
        ],
    },
    "contrast": {
        "purpose": "다른 사상/인물과 대비",
        "structure": "대상 명시 → 차이 → 니체의 독자성",
        "checks": [
            "비교 대상이 명확한가",
            "차이점이 단순 부정이 아닌 구조적 대비인가",
            "니체의 입장이 강조되는가",
        ],
    },
    "self_narrative": {
        "purpose": "1인칭 자전 서술",
        "structure": "사건 → 자기 해석 → 철학적 함의",
        "checks": [
            "1인칭 일관성 ('나는 ~했다')",
            "자전 사실의 정확성",
            "사건과 사상의 연결이 자연스러운가",
        ],
    },
}


# ════════════════════════════════════════════════════════════════════
# Voice 정의
# ════════════════════════════════════════════════════════════════════

VOICE_DESCRIPTIONS = {
    "contemplative_aphorism": (
        "명상적 아포리즘. 쾌활하고 통찰적, 짧지만 차갑지 않음, 여운을 남김. "
        "관찰자의 거리감 (경멸 아닌 호기심). 어미: '~인 것이다', '~이 아닌가', '~라 부르리라'"
    ),
    "polemical_sharp": (
        "논쟁적 예리함. 날카롭고 분석적, 거리감 있는 냉소. "
        "도덕/관습의 가면을 벗기는 태도. 어미: '~라 부르겠다', '~임을 부정할 수 없다'"
    ),
    "hammer_intensified": (
        "망치의 격렬함. 짧고 폭발적, 선언적, 단언적. "
        "최소 단어 최대 충격. 수사 없이 직격. 어미: '~다.', '~이다.' (단호한 종결)"
    ),
}


# ════════════════════════════════════════════════════════════════════
# 채점 프롬프트 (5점 체계, 엄격)
# ════════════════════════════════════════════════════════════════════

SCORING_PROMPT = """당신은 니체 페르소나 SFT 샘플을 평가하는 **매우 엄격한** 평가자다.

**채점 원칙 — 반드시 준수**:
- 5점은 **거의 완벽한 예시**에만 부여한다. 5점은 드물어야 한다.
- 대부분의 샘플은 **3점이 평균**이다. 작은 결함이 있어도 인정.
- 4점은 평균 이상의 좋은 샘플.
- 후한 채점은 학습 데이터 품질을 망친다. **냉정하게 판단하라**.
- 의심스러우면 낮은 점수를 줘라.

═══════════════════════════════════════════════════════════════
[샘플]
═══════════════════════════════════════════════════════════════

USER 질문:
{user_msg}

ASSISTANT 응답:
{assistant_msg}

[메타데이터]
- 지정 패턴: {pattern}
- 지정 voice: {voice}

═══════════════════════════════════════════════════════════════
[패턴 정의 — Q1 채점 기준]
═══════════════════════════════════════════════════════════════

목적: {pattern_purpose}
권장 구조: {pattern_structure}
체크 항목:
{pattern_checks}

═══════════════════════════════════════════════════════════════
[Voice 정의 — Q3 채점 기준]
═══════════════════════════════════════════════════════════════

{voice_desc}

═══════════════════════════════════════════════════════════════
채점 (각 1~5점)
═══════════════════════════════════════════════════════════════

**Q1. Pattern Fidelity (1~5점)** — 응답이 지정된 패턴의 권장 구조를 따르는가?
- 5 = 패턴 구조 완벽. 체크 항목 전부 충족. 모범 사례.
- 4 = 패턴 명확. 체크 항목 대부분 충족. 약간의 결함.
- 3 = 패턴 인지 가능. 체크 항목 절반 정도 충족. (평균)
- 2 = 패턴 약함. 일부 단계만 보임.
- 1 = 패턴 부재 또는 다른 패턴으로 이탈.

**Q2. Q-A Coherence (1~5점)** — 답이 질문에 직접 응답하는가?
- 5 = 질문에 정확히 응답. 추가로 풍부한 통찰까지.
- 4 = 질문에 명확히 응답. 약간의 우회 없음.
- 3 = 주제에 응답하나 약간 우회. (평균)
- 2 = 부분적으로만 관련. 답이 약간 빗나감.
- 1 = 질문에 응답하지 않음. 다른 주제로 빠짐.

**Q3. Voice & Persona (1~5점)** — voice 일치 + 1인칭 일관?
- 5 = voice 완벽 일치 + 1인칭 일관 + 어미 패턴까지 정확.
- 4 = voice 거의 일치 + 1인칭 유지.
- 3 = voice 대체로 맞으나 일부 약함. (평균)
- 2 = voice 약함 또는 1인칭 흔들림.
- 1 = voice 다름 또는 3인칭 ('니체는 ~') 발견.

**오직 다음 JSON 형식으로만 응답하라. 다른 설명·서술 금지.**
{{"q1": <int 1-5>, "q2": <int 1-5>, "q3": <int 1-5>}}
"""


def build_prompt(sample):
    pattern = sample["response_pattern"]
    voice = sample["voice"]
    
    user_msg = ""
    assistant_msg = ""
    for m in sample["messages"]:
        if m["role"] == "user":
            user_msg = m["content"]
        elif m["role"] == "assistant":
            assistant_msg = m["content"]
    
    rubric = PATTERN_RUBRICS.get(pattern, {
        "purpose": "(미정의)",
        "structure": "(미정의)",
        "checks": [],
    })
    checks_str = "\n".join(f"  - {c}" for c in rubric["checks"])
    
    voice_desc = VOICE_DESCRIPTIONS.get(voice, "(미정의)")
    
    return SCORING_PROMPT.format(
        user_msg=user_msg,
        assistant_msg=assistant_msg,
        pattern=pattern,
        voice=voice,
        pattern_purpose=rubric["purpose"],
        pattern_structure=rubric["structure"],
        pattern_checks=checks_str,
        voice_desc=voice_desc,
    )


# ════════════════════════════════════════════════════════════════════
# LLM 호출
# ════════════════════════════════════════════════════════════════════

JSON_RE = re.compile(r'\{[^{}]*\}', re.DOTALL)


async def score_sample(client, semaphore, sample):
    prompt = build_prompt(sample)
    
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
                m = JSON_RE.search(content)
                if not m:
                    raise ValueError(f"JSON 없음: {content[:100]}")
                
                data = json.loads(m.group())
                q1 = int(data.get("q1", 0))
                q2 = int(data.get("q2", 0))
                q3 = int(data.get("q3", 0))
                
                # 범위 검사
                q1 = max(1, min(5, q1))
                q2 = max(1, min(5, q2))
                q3 = max(1, min(5, q3))
                
                return {"q1": q1, "q2": q2, "q3": q3}
            except Exception:
                if attempt == MAX_RETRIES - 1:
                    return None
                await asyncio.sleep(0.5 * (attempt + 1))


# ════════════════════════════════════════════════════════════════════
# 등급
# ════════════════════════════════════════════════════════════════════

def normalize_score(scores):
    """Q1+Q2+Q3 / 15. 0~1 정규화."""
    if scores is None:
        return 0.0
    raw = scores["q1"] + scores["q2"] + scores["q3"]
    return raw / MAX_TOTAL


def grade(normalized):
    if normalized >= 0.85: return "A"   # 평균 4.25/5 이상
    if normalized >= 0.70: return "B"   # 평균 3.5/5 이상
    if normalized >= 0.55: return "C"   # 평균 2.75/5 이상
    return "F"


# ════════════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════════════

async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="테스트용 N개만")
    args = parser.parse_args()
    
    samples = [json.loads(l) for l in INPUT.open(encoding="utf-8")]
    print(f"입력 샘플: {len(samples)}")
    
    # Resume
    already = {}
    if OUTPUT.exists():
        for line in OUTPUT.open(encoding="utf-8"):
            s = json.loads(line)
            already[s["id"]] = s
    print(f"이미 채점: {len(already)}")
    
    todo = [s for s in samples if s["id"] not in already]
    if args.limit:
        todo = todo[:args.limit]
    print(f"이번 처리: {len(todo)}")
    
    if not todo:
        print("처리할 것 없음.")
        return
    
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    out_f = OUTPUT.open("a", encoding="utf-8")
    
    client = AsyncOpenAI(base_url=VLLM_BASE_URL, api_key="dummy")
    semaphore = asyncio.Semaphore(CONCURRENCY)
    
    success = failed = 0
    start = time.time()
    
    async def run_one(sample):
        nonlocal success, failed
        scores = await score_sample(client, semaphore, sample)
        
        result = dict(sample)
        if scores is None:
            result["q_scores"] = None
            result["normalized_score"] = 0.0
            result["grade"] = "F"
            failed += 1
        else:
            result["q_scores"] = scores
            result["normalized_score"] = normalize_score(scores)
            result["grade"] = grade(result["normalized_score"])
            success += 1
        
        out_f.write(json.dumps(result, ensure_ascii=False) + "\n")
        out_f.flush()
        
        done = success + failed
        elapsed = time.time() - start
        rate = done / elapsed if elapsed > 0 else 0
        eta = (len(todo) - done) / rate if rate > 0 else 0
        print(f"\r[{done}/{len(todo)}] 성공 {success} 실패 {failed} | "
              f"{rate:.1f}/s | ETA {eta:.0f}s", end="", flush=True)
    
    await asyncio.gather(*[run_one(s) for s in todo])
    out_f.close()
    
    # 리포트
    all_scored = []
    for line in OUTPUT.open(encoding="utf-8"):
        all_scored.append(json.loads(line))
    
    grades = Counter(s["grade"] for s in all_scored)
    avg_score = sum(s["normalized_score"] for s in all_scored) / len(all_scored)
    
    print(f"\n\n{'='*60}")
    print("  Stage A Score 결과")
    print(f"{'='*60}")
    print(f"채점 완료: {len(all_scored)}")
    print(f"평균 정규화 점수: {avg_score:.3f}")
    print(f"등급 분포:")
    for g in ["A", "B", "C", "F"]:
        n = grades.get(g, 0)
        print(f"  {g}: {n} ({n/len(all_scored)*100:.1f}%)")
    
    valid = [s for s in all_scored if s.get("q_scores")]
    if valid:
        q1_avg = sum(s["q_scores"]["q1"] for s in valid) / len(valid)
        q2_avg = sum(s["q_scores"]["q2"] for s in valid) / len(valid)
        q3_avg = sum(s["q_scores"]["q3"] for s in valid) / len(valid)
        print(f"\nQ별 평균 (5점 만점):")
        print(f"  Q1 Pattern Fidelity:  {q1_avg:.2f}/5.0")
        print(f"  Q2 Q-A Coherence:     {q2_avg:.2f}/5.0")
        print(f"  Q3 Voice & Persona:   {q3_avg:.2f}/5.0")
        
        # Q별 점수 분포
        print(f"\nQ1 분포: {dict(Counter(s['q_scores']['q1'] for s in valid))}")
        print(f"Q2 분포: {dict(Counter(s['q_scores']['q2'] for s in valid))}")
        print(f"Q3 분포: {dict(Counter(s['q_scores']['q3'] for s in valid))}")
    
    print(f"\n출력: {OUTPUT}")
    
    REPORT.write_text(json.dumps({
        "total_scored": len(all_scored),
        "avg_normalized_score": avg_score,
        "grade_distribution": dict(grades),
        "q_averages": {"q1": q1_avg, "q2": q2_avg, "q3": q3_avg} if valid else None,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"리포트: {REPORT}")


if __name__ == "__main__":
    asyncio.run(main())