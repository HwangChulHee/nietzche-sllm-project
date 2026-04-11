"""Stage C — Score: Stage B 응답의 LLM judge 채점.

각 응답을 Stage A와 동일 루브릭(Q1 Pattern + Q2 Coherence + Q3 Voice)으로 채점.
응답이 붕괴(token collapse)된 경우 heuristic으로 사전 감지하여 자동 최소점 처리.

[--with-reasoning 플래그]
 축별 reasoning을 함께 생성. G-Eval 방식(reason을 score보다 먼저 생성)을 따름.
 출력이 scored.jsonl이 아닌 scored_cot.jsonl로 분리되어 기존 결과는 보존됨.

입력:
  - finetune/outputs/stage_b/responses.jsonl  (828, generated + meta)
  - v2_data/sft_dataset/eval.jsonl            (138, pattern/voice lookup)

출력 (모드별 분리):
  점수만    → finetune/outputs/stage_c/scored.jsonl
             finetune/outputs/stage_c/scored_report.json
  CoT 모드  → finetune/outputs/stage_c/scored_cot.jsonl
             finetune/outputs/stage_c/scored_cot_report.json

사용법:
  bash finetune/scripts/run_judge_server.sh                    # 먼저 judge 서버 기동
  python finetune/scripts/stage_c_score.py --limit 20          # 점수만 (스모크)
  python finetune/scripts/stage_c_score.py                     # 점수만 (본 실행)
  python finetune/scripts/stage_c_score.py --with-reasoning --limit 20
  python finetune/scripts/stage_c_score.py --with-reasoning    # CoT 본 실행
"""
import asyncio
import json
import time
from collections import Counter, defaultdict
from pathlib import Path

from openai import AsyncOpenAI

# ════════════════════════════════════════════════════════════════════
# 경로 (스크립트 위치 기반 — cwd 무관)
# ════════════════════════════════════════════════════════════════════

SCRIPT_DIR = Path(__file__).resolve().parent          # ml/finetune/scripts
ML_ROOT = SCRIPT_DIR.parent.parent                     # ml/

INPUT_RESPONSES = ML_ROOT / "finetune/outputs/stage_b/responses.jsonl"
INPUT_EVAL = ML_ROOT / "v2_data/sft_dataset/eval.jsonl"
STAGE_C_DIR = ML_ROOT / "finetune/outputs/stage_c"

# OUTPUT / REPORT는 main()에서 모드에 따라 결정됨

# ════════════════════════════════════════════════════════════════════
# LLM 설정
# ════════════════════════════════════════════════════════════════════

VLLM_BASE_URL = "http://localhost:8000/v1"
MODEL = "google/gemma-4-26B-A4B-it"    # Stage A와 동일 judge (점수 축 호환성)
CONCURRENCY = 16
MAX_RETRIES = 3
REQUEST_TIMEOUT = 60.0                 # 초. stuck 응답 방지
TEMPERATURE = 0.2
MAX_TOKENS_PLAIN = 300                 # 점수만
MAX_TOKENS_COT = 700                   # reasoning 포함 (한국어 기준 여유)

MAX_TOTAL = 15.0                       # Q1(5) + Q2(5) + Q3(5)

# Judge 프롬프트 길이 안전장치
MAX_RESPONSE_CHARS_FOR_JUDGE = 3000


# ════════════════════════════════════════════════════════════════════
# Collapse 사전 감지 (heuristic pre-filter)
# ════════════════════════════════════════════════════════════════════

COLLAPSE_MAX_RUN = 30
COLLAPSE_MIN_CHAR_DIVERSITY = 0.05
COLLAPSE_NGRAM_K = 10
COLLAPSE_NGRAM_MIN_DISTINCT = 0.15
COLLAPSE_LONG_LEN = 3000
COLLAPSE_LONG_CHAR_DIVERSITY = 0.15


def detect_collapse(text: str) -> tuple[bool, str]:
    """응답 붕괴 감지. (붕괴 여부, 사유 문자열) 반환."""
    if not text:
        return True, "empty"

    n = len(text)

    # R1: 동일 문자 연속 — early return으로 효율화
    cur_run = 1
    for i in range(1, n):
        if text[i] == text[i - 1]:
            cur_run += 1
            if cur_run >= COLLAPSE_MAX_RUN:
                return True, f"max_run={cur_run}"
        else:
            cur_run = 1

    # R2: 전체 문자 다양성
    char_diversity = len(set(text)) / n
    if char_diversity < COLLAPSE_MIN_CHAR_DIVERSITY:
        return True, f"char_diversity={char_diversity:.3f}"

    # R3: 10-gram distinct ratio
    if n >= COLLAPSE_NGRAM_K * 5:
        ngrams = [text[i:i + COLLAPSE_NGRAM_K] for i in range(n - COLLAPSE_NGRAM_K + 1)]
        distinct_ratio = len(set(ngrams)) / len(ngrams)
        if distinct_ratio < COLLAPSE_NGRAM_MIN_DISTINCT:
            return True, f"ngram_distinct={distinct_ratio:.3f}"

    # R4: 길이 + 다양성 복합
    if n >= COLLAPSE_LONG_LEN and char_diversity < COLLAPSE_LONG_CHAR_DIVERSITY:
        return True, f"long_low_diversity=n{n}_d{char_diversity:.3f}"

    return False, ""


# ════════════════════════════════════════════════════════════════════
# 패턴 / Voice 정의 (Stage A와 동일)
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
# 채점 프롬프트 — 두 버전
# ════════════════════════════════════════════════════════════════════

_COMMON_PROMPT_HEADER = """당신은 니체 페르소나 sLLM이 생성한 응답을 평가하는 **매우 엄격한** 평가자다.

**채점 원칙 — 반드시 준수**:
- 5점은 **거의 완벽한 예시**에만 부여한다. 5점은 드물어야 한다.
- 대부분의 응답은 **3점이 평균**이다. 작은 결함이 있어도 인정.
- 4점은 평균 이상의 좋은 응답.
- 후한 채점은 평가의 신뢰를 망친다. **냉정하게 판단하라**.
- 의심스러우면 낮은 점수를 줘라.

═══════════════════════════════════════════════════════════════
[응답]
═══════════════════════════════════════════════════════════════

USER 질문:
{user_msg}

모델 응답:
{assistant_msg}

[메타데이터]
- 기대 패턴: {pattern}
- 기대 voice: {voice}

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
"""


SCORING_PROMPT_PLAIN = _COMMON_PROMPT_HEADER + """
**오직 다음 JSON 형식으로만 응답하라. 다른 설명·서술 금지.**
{{"q1": <int 1-5>, "q2": <int 1-5>, "q3": <int 1-5>}}
"""


SCORING_PROMPT_COT = _COMMON_PROMPT_HEADER + """
**오직 다음 JSON 형식으로만 응답하라. 반드시 각 축의 reason을 먼저 작성한 뒤 점수를 매겨라.**

**reason 작성 규칙** (반드시 준수):
- 한국어, 각 1~2문장
- **구체적 근거** 제시: 응답의 어떤 부분이 해당 점수의 근거인지 명시
- 추상적 평가 금지: "좋음", "나쁨", "적절함" 등 혼자서는 의미 없는 단어 사용 X
- Q1은 패턴 체크 항목 중 어느 것이 충족/미충족됐는지, Q2는 질문과 답의 정합성, Q3는 voice 특징(특히 어미)이 맞는지를 언급

{{
  "q1_reason": "<패턴 구조 관점의 구체적 근거>",
  "q1": <int 1-5>,
  "q2_reason": "<질문-답 직접성 관점의 구체적 근거>",
  "q2": <int 1-5>,
  "q3_reason": "<voice 특징 및 어미 일치도 관점의 구체적 근거>",
  "q3": <int 1-5>
}}
"""


def build_prompt(response_row: dict, eval_meta: dict, with_reasoning: bool) -> str:
    pattern = eval_meta["response_pattern"]
    voice = eval_meta["voice"]

    user_msg = ""
    for m in response_row.get("input_messages", []):
        if m["role"] == "user":
            user_msg = m["content"]
            break

    assistant_msg = response_row["generated"][:MAX_RESPONSE_CHARS_FOR_JUDGE]

    rubric = PATTERN_RUBRICS.get(pattern, {
        "purpose": "(미정의)",
        "structure": "(미정의)",
        "checks": [],
    })
    checks_str = "\n".join(f"  - {c}" for c in rubric["checks"])
    voice_desc = VOICE_DESCRIPTIONS.get(voice, "(미정의)")

    template = SCORING_PROMPT_COT if with_reasoning else SCORING_PROMPT_PLAIN
    return template.format(
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
# LLM 호출 + Robust JSON 파서
# ════════════════════════════════════════════════════════════════════

def parse_json_response(content: str) -> dict | None:
    """LLM 응답에서 첫 번째 유효한 JSON 객체 추출.

    reason 필드에 중괄호·따옴표가 들어갈 수 있어 regex 대신
    json.JSONDecoder.raw_decode 사용 — trailing 문자 허용.
    """
    start = content.find('{')
    if start == -1:
        return None
    decoder = json.JSONDecoder()
    try:
        obj, _ = decoder.raw_decode(content[start:])
        return obj
    except json.JSONDecodeError:
        return None


async def score_sample(client, semaphore, response_row, eval_meta, with_reasoning):
    """Judge 호출. (scores_dict, reasons_dict_or_None) 반환. 실패 시 (None, None)."""
    prompt = build_prompt(response_row, eval_meta, with_reasoning)
    max_tokens = MAX_TOKENS_COT if with_reasoning else MAX_TOKENS_PLAIN

    async with semaphore:
        for attempt in range(MAX_RETRIES):
            try:
                resp = await client.chat.completions.create(
                    model=MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=TEMPERATURE,
                    max_tokens=max_tokens,
                )
                content = resp.choices[0].message.content.strip()
                obj = parse_json_response(content)
                if obj is None:
                    raise ValueError(f"JSON parse fail: {content[:120]}")

                q1 = max(1, min(5, int(obj.get("q1", 0))))
                q2 = max(1, min(5, int(obj.get("q2", 0))))
                q3 = max(1, min(5, int(obj.get("q3", 0))))
                scores = {"q1": q1, "q2": q2, "q3": q3}

                reasons = None
                if with_reasoning:
                    reasons = {
                        "q1": str(obj.get("q1_reason", ""))[:600],
                        "q2": str(obj.get("q2_reason", ""))[:600],
                        "q3": str(obj.get("q3_reason", ""))[:600],
                    }
                return scores, reasons
            except Exception:
                if attempt == MAX_RETRIES - 1:
                    return None, None
                await asyncio.sleep(0.5 * (attempt + 1))


def normalize_score(scores):
    if scores is None:
        return 0.0
    return (scores["q1"] + scores["q2"] + scores["q3"]) / MAX_TOTAL


def grade(normalized):
    if normalized >= 0.85: return "A"
    if normalized >= 0.70: return "B"
    if normalized >= 0.55: return "C"
    return "F"


def make_key(sample_id: str, model_tag: str) -> str:
    return f"{sample_id}::{model_tag}"


# ════════════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════════════

async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="테스트용 N개만")
    parser.add_argument("--model-filter", type=str,
                        help="특정 model_tag만 처리 (쉼표 구분)")
    parser.add_argument("--with-reasoning", action="store_true",
                        help="축별 reasoning 포함 (G-Eval 방식). "
                             "출력이 scored_cot.jsonl로 분리되어 기존 결과 보존.")
    args = parser.parse_args()

    with_reasoning = args.with_reasoning

    # 출력 경로 모드별 분리
    if with_reasoning:
        output_path = STAGE_C_DIR / "scored_cot.jsonl"
        report_path = STAGE_C_DIR / "scored_cot_report.json"
        mode_label = "CoT (reasoning 포함)"
    else:
        output_path = STAGE_C_DIR / "scored.jsonl"
        report_path = STAGE_C_DIR / "scored_report.json"
        mode_label = "점수만"

    print(f"Mode: {mode_label}")
    print(f"Output: {output_path}")

    # 입력 파일 존재 확인
    if not INPUT_RESPONSES.exists():
        raise SystemExit(f"입력 없음: {INPUT_RESPONSES}\n  Stage B 먼저 실행 필요.")
    if not INPUT_EVAL.exists():
        raise SystemExit(f"입력 없음: {INPUT_EVAL}")

    # eval.jsonl 로드
    eval_meta = {}
    for line in INPUT_EVAL.open(encoding="utf-8"):
        row = json.loads(line)
        eval_meta[row["id"]] = row
    print(f"eval 메타 로드: {len(eval_meta)}")

    # responses.jsonl 로드
    responses = [json.loads(l) for l in INPUT_RESPONSES.open(encoding="utf-8")]
    print(f"입력 응답: {len(responses)}")

    if args.model_filter:
        tags = set(args.model_filter.split(","))
        responses = [r for r in responses if r["model_tag"] in tags]
        print(f"모델 필터 후: {len(responses)} ({sorted(tags)})")

    # Resume: 이미 채점된 (sample_id, model_tag) 스킵
    already = {}
    if output_path.exists():
        for line in output_path.open(encoding="utf-8"):
            s = json.loads(line)
            already[make_key(s["sample_id"], s["model_tag"])] = s
    print(f"이미 채점: {len(already)}")

    todo = [
        r for r in responses
        if make_key(r["sample_id"], r["model_tag"]) not in already
    ]
    if args.limit:
        todo = todo[:args.limit]
    print(f"이번 처리: {len(todo)}")

    if not todo:
        print("처리할 것 없음. 요약만 출력.")
        print_report(output_path, report_path)
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    out_f = output_path.open("a", encoding="utf-8")

    client = AsyncOpenAI(
        base_url=VLLM_BASE_URL,
        api_key="dummy",
        timeout=REQUEST_TIMEOUT,
    )
    semaphore = asyncio.Semaphore(CONCURRENCY)
    lock = asyncio.Lock()

    success = failed = collapsed = 0
    start = time.time()

    async def run_one(response_row):
        nonlocal success, failed, collapsed

        sample_id = response_row["sample_id"]
        model_tag = response_row["model_tag"]
        generated = response_row.get("generated", "")

        meta = eval_meta.get(sample_id)
        if meta is None:
            result = {
                "sample_id": sample_id,
                "model_tag": model_tag,
                "response_pattern": None,
                "voice": None,
                "question_type": None,
                "generated_len": len(generated),
                "collapsed": False,
                "collapse_reason": "",
                "q_scores": None,
                "q_reasons": None,
                "normalized_score": 0.0,
                "grade": "F",
                "error": "eval_meta_missing",
            }
            async with lock:
                out_f.write(json.dumps(result, ensure_ascii=False) + "\n")
                out_f.flush()
                failed += 1
            return

        # Collapse 사전 감지
        is_collapsed, reason = detect_collapse(generated)
        if is_collapsed:
            scores = {"q1": 1, "q2": 1, "q3": 1}
            # Collapse 샘플은 judge 호출 없이 고정 reason 부여
            if with_reasoning:
                collapse_desc = f"응답 붕괴 감지 (heuristic: {reason}). judge 호출 없이 자동 최소점 부여."
                reasons = {
                    "q1": collapse_desc,
                    "q2": collapse_desc,
                    "q3": collapse_desc,
                }
            else:
                reasons = None
        else:
            scores, reasons = await score_sample(
                client, semaphore, response_row, meta, with_reasoning
            )

        norm = normalize_score(scores)
        result = {
            "sample_id": sample_id,
            "model_tag": model_tag,
            "response_pattern": meta.get("response_pattern"),
            "voice": meta.get("voice"),
            "question_type": meta.get("question_type"),
            "use_case": meta.get("use_case"),
            "difficulty": meta.get("difficulty"),
            "generated_len": len(generated),
            "gen_time_sec": response_row.get("gen_time_sec"),
            "collapsed": is_collapsed,
            "collapse_reason": reason,
            "q_scores": scores,
            "q_reasons": reasons,
            "normalized_score": norm,
            "grade": grade(norm),
        }

        async with lock:
            if is_collapsed:
                collapsed += 1
                success += 1
            elif scores is None:
                failed += 1
            else:
                success += 1

            out_f.write(json.dumps(result, ensure_ascii=False) + "\n")
            out_f.flush()

            done = success + failed
            elapsed = time.time() - start
            rate = done / elapsed if elapsed > 0 else 0
            eta = (len(todo) - done) / rate if rate > 0 else 0
            print(
                f"\r[{done}/{len(todo)}] 성공 {success} "
                f"(이번 실행 붕괴 {collapsed}) 실패 {failed} | "
                f"{rate:.1f}/s | ETA {eta:.0f}s",
                end="", flush=True,
            )

    await asyncio.gather(*[run_one(r) for r in todo])
    out_f.close()
    print()

    print_report(output_path, report_path)


def print_report(output_path: Path, report_path: Path):
    """채점 직후 간단 요약 (상세 breakdown은 stage_c_report.py)."""
    if not output_path.exists():
        print("결과 파일 없음.")
        return

    rows = [json.loads(l) for l in output_path.open(encoding="utf-8")]
    if not rows:
        return

    by_model = defaultdict(list)
    for r in rows:
        by_model[r["model_tag"]].append(r)

    print(f"\n{'=' * 74}")
    print(f"  Stage C Score 요약 ({output_path.name})")
    print(f"{'=' * 74}")
    print(f"총 채점: {len(rows)}")
    print()
    print(f"{'model':<12} {'n':>4} {'mean':>7} {'Q1':>6} {'Q2':>6} {'Q3':>6} "
          f"{'coll':>5} {'A':>4} {'B':>4} {'C':>4} {'F':>4}")
    print("-" * 74)

    model_order = ["baseline", "epoch1", "epoch2", "epoch3", "epoch4", "epoch5"]
    report_data = {}
    for model in model_order:
        if model not in by_model:
            continue
        items = by_model[model]
        valid = [r for r in items if r.get("q_scores")]
        if not valid:
            continue
        mean_score = sum(r["normalized_score"] for r in valid) / len(valid)
        q1 = sum(r["q_scores"]["q1"] for r in valid) / len(valid)
        q2 = sum(r["q_scores"]["q2"] for r in valid) / len(valid)
        q3 = sum(r["q_scores"]["q3"] for r in valid) / len(valid)
        n_collapsed = sum(1 for r in items if r.get("collapsed"))
        g = Counter(r["grade"] for r in items)

        print(f"{model:<12} {len(items):>4} {mean_score:>7.3f} "
              f"{q1:>6.2f} {q2:>6.2f} {q3:>6.2f} {n_collapsed:>5} "
              f"{g.get('A',0):>4} {g.get('B',0):>4} {g.get('C',0):>4} {g.get('F',0):>4}")

        report_data[model] = {
            "n": len(items),
            "mean_normalized": mean_score,
            "q1_mean": q1,
            "q2_mean": q2,
            "q3_mean": q3,
            "collapsed": n_collapsed,
            "grade_dist": dict(g),
        }

    if report_data:
        best = max(
            report_data.items(),
            key=lambda kv: (kv[1]["mean_normalized"], kv[1]["q3_mean"]),
        )
        print(f"\n>> Best model: {best[0]} "
              f"(mean={best[1]['mean_normalized']:.3f}, "
              f"Q3={best[1]['q3_mean']:.2f}, "
              f"collapsed={best[1]['collapsed']})")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n리포트: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
