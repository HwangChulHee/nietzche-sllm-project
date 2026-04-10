"""Test A: vLLM baseline generation on Gemma 4 31B-it.

목적:
  1. vLLM이 Gemma 4 31B를 로드할 수 있는지 (cu128 vs driver 12.7 호환 확인)
  2. enforce_eager=True + max_model_len=1024 최적화가 동작하는지
  3. 138개 eval 샘플 생성이 얼마나 걸리는지 실측
  4. baseline 응답을 저장 (나중에 Stage B 본 실행에서 재사용)

실행:
  cd /workspace/nietzche-sllm-project/ml
  source .venv/bin/activate
  python finetune/scripts/test_a_vllm_baseline.py 2>&1 | tee finetune/logs/test_a.log

성공 기준:
  - vLLM 로드 성공 (기대 ~3분)
  - 138개 생성 완료 (기대 ~2~3분)
  - 생성된 응답이 한국어 니체 톤
  - test_a_baseline.jsonl 저장

실패 시 확인 포인트:
  - vLLM 로드 에러: transformers 5.5 vs vllm 0.19 metadata 충돌 가능
  - OOM: gpu_memory_utilization을 0.85로 낮추기
  - 로드 느림: HF cache에 모델 있는지 확인 (du -sh ~/.cache/huggingface)
"""
import json
import time
from pathlib import Path

print("=" * 60)
print("Test A: vLLM baseline generation")
print("=" * 60)

# ─────────────────────────────────────────────────────────
# 1. eval set 로드
# ─────────────────────────────────────────────────────────
EVAL_PATH = Path("/workspace/nietzche-sllm-project/ml/v2_data/sft_dataset/eval.jsonl")
samples = [json.loads(l) for l in EVAL_PATH.open(encoding="utf-8")]
print(f"\n[1] Loaded {len(samples)} eval samples from {EVAL_PATH.name}")

# ─────────────────────────────────────────────────────────
# 2. vLLM 로드 (타이머 시작)
# ─────────────────────────────────────────────────────────
print(f"\n[2] Loading vLLM...")
print(f"    model: google/gemma-4-31B-it")
print(f"    dtype: bfloat16")
print(f"    max_model_len: 1024")
print(f"    enforce_eager: True")
print(f"    gpu_memory_utilization: 0.90")

t0 = time.time()
from vllm import LLM, SamplingParams

llm = LLM(
    model="google/gemma-4-31B-it",
    dtype="bfloat16",
    max_model_len=1024,
    enforce_eager=True,
    gpu_memory_utilization=0.90,
)
load_time = time.time() - t0
print(f"\n    ✓ Load time: {load_time:.1f}s ({load_time/60:.1f} min)")

# ─────────────────────────────────────────────────────────
# 3. Prompt 생성 (chat template 적용)
# ─────────────────────────────────────────────────────────
print(f"\n[3] Building prompts with chat template...")
tokenizer = llm.get_tokenizer()
prompts = []
for s in samples:
    # messages[0] = system, messages[1] = user, messages[2] = assistant (reference, 제외)
    msgs = s["messages"][:2]
    prompt = tokenizer.apply_chat_template(
        msgs,
        tokenize=False,
        add_generation_prompt=True,  # assistant 차례를 열어주는 토큰 추가
    )
    prompts.append(prompt)

print(f"    ✓ Built {len(prompts)} prompts")
print(f"\n    --- First prompt preview ---")
print(prompts[0][:600])
print(f"    --- end preview ---")

# ─────────────────────────────────────────────────────────
# 4. 생성 (greedy, max_tokens=512)
# ─────────────────────────────────────────────────────────
print(f"\n[4] Generating {len(prompts)} responses (greedy, max_tokens=512)...")
sampling = SamplingParams(
    temperature=0.0,  # greedy for reproducibility + fair model comparison
    max_tokens=512,   # hard difficulty (7~12 sentences) 기준 넉넉히
)

t0 = time.time()
outputs = llm.generate(prompts, sampling)
gen_time = time.time() - t0

print(f"\n    ✓ Generation time: {gen_time:.1f}s ({gen_time/60:.1f} min)")
print(f"    Per-sample avg: {gen_time / len(prompts):.2f}s")

# ─────────────────────────────────────────────────────────
# 5. 샘플 출력 확인 (첫 3개)
# ─────────────────────────────────────────────────────────
print(f"\n[5] First 3 outputs (sanity check):")
for i in range(min(3, len(outputs))):
    s = samples[i]
    gen_text = outputs[i].outputs[0].text
    print(f"\n    --- Sample {i} (id={s['id']}, voice={s['voice']}) ---")
    print(f"    SYSTEM:  {s['messages'][0]['content'][:100]}")
    print(f"    USER:    {s['messages'][1]['content'][:150]}")
    print(f"    GEN:     {gen_text[:300]}")
    if len(gen_text) > 300:
        print(f"             ... ({len(gen_text)} chars total)")

# ─────────────────────────────────────────────────────────
# 6. 저장
# ─────────────────────────────────────────────────────────
OUT_DIR = Path("/workspace/nietzche-sllm-project/ml/finetune/outputs/stage_b_test")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = OUT_DIR / "test_a_baseline.jsonl"

with OUT_PATH.open("w", encoding="utf-8") as f:
    for s, out in zip(samples, outputs):
        record = {
            "sample_id": s["id"],
            "model_tag": "baseline",
            "voice": s["voice"],
            "response_pattern": s["response_pattern"],
            "use_case": s["use_case"],
            "difficulty": s["difficulty"],
            "messages": s["messages"][:2],  # system + user (평가용 입력)
            "reference": s["messages"][2]["content"],  # 원본 assistant (참고용)
            "generated": out.outputs[0].text,
            "gen_tokens": len(out.outputs[0].token_ids),
        }
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

print(f"\n[6] Saved {len(outputs)} responses to:")
print(f"    {OUT_PATH}")

# ─────────────────────────────────────────────────────────
# 7. 요약 + Stage B 본 실행 시간 예측
# ─────────────────────────────────────────────────────────
total = load_time + gen_time
print(f"\n{'=' * 60}")
print(f"SUMMARY")
print(f"{'=' * 60}")
print(f"  vLLM load:  {load_time:>6.1f}s  ({load_time/60:>4.1f} min)")
print(f"  Generation: {gen_time:>6.1f}s  ({gen_time/60:>4.1f} min)")
print(f"  Total:      {total:>6.1f}s  ({total/60:>4.1f} min)")
print(f"\nProjection for full Stage B (baseline + 5 epoch = 6 models):")
print(f"  Naive serial:   {total * 6 / 60:.1f} min (no optimization)")
print(f"  With merge overhead (+4 min/epoch × 5 = 20 min):")
print(f"                  {(total * 6 + 20 * 60) / 60:.1f} min")
print(f"\n  ※ 이 시간은 merge 병렬화 없이 순차 실행 기준")
print(f"  ※ 파이프라이닝 적용 시 더 단축 가능 (CPU merge + GPU gen 병행)")

# 응답 토큰 길이 분포 (오버핏/루프 검출 힌트)
lengths = [len(o.outputs[0].token_ids) for o in outputs]
print(f"\n  생성 길이 통계 (tokens):")
print(f"    min={min(lengths)}, max={max(lengths)}, "
      f"avg={sum(lengths)/len(lengths):.1f}")

# 512에 도달한 비율 (잘린 응답 = 루프 또는 긴 응답)
truncated = sum(1 for l in lengths if l >= 512)
if truncated > 0:
    print(f"    ⚠ max_tokens(512)에 도달: {truncated}/{len(lengths)} "
          f"({truncated/len(lengths)*100:.0f}%)")
    print(f"      → 루프/반복 가능성 또는 길이 부족")

print(f"\n{'=' * 60}")
print("Test A 완료. 로그 확인 후 Test B(merge) 또는 Stage B 본 실행으로 진행.")
print(f"{'=' * 60}")