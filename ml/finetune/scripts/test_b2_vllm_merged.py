"""Test B-2: Load merged epoch1 model in vLLM and generate 5 sample responses.

목적:
  - 리스크 B: vLLM이 peft-merged Gemma 4 모델을 로드할 수 있는가?
  - 리스크 C: 로드된 merged model의 생성 품질이 baseline과 다른가?

환경:
  ml venv (torch 2.10 + vllm 0.19 + transformers 5.5)

전제:
  Test B-1이 성공해서 /workspace/.../merged/epoch1/ 에 62GB 모델이 저장됨.

실행:
  cd /workspace/nietzche-sllm-project/ml
  source .venv/bin/activate
  python finetune/scripts/test_b2_vllm_merged.py 2>&1 | tee finetune/logs/test_b2.log

성공 기준:
  - vLLM 로드 성공 (기대 ~8분, baseline과 비슷)
  - 5개 생성 성공
  - 응답이 한국어 니체 톤 유지
  - **핵심**: 응답이 baseline과 달라야 함 (LoRA가 실제로 반영됐다는 증거)
    - 길이 차이 (baseline 평균 600 → epoch1 기대 ~280)
    - 구조 차이 (3단 구조 준수 여부)
    - 어조 차이 (연기 지시문, 볼드 헤더 감소)

실패 시:
  - 로드 실패 → key 이름 불일치 가능. Unsloth로 재merge 필요
  - 로드는 되지만 생성이 이상 → LoRA weight가 제대로 반영 안 됨
    (baseline과 거의 동일하게 나오면 merge가 이상한 것)
"""
import json
import time
from pathlib import Path

print("=" * 60)
print("Test B-2: vLLM load merged epoch1 + generate 5 samples")
print("=" * 60)

MERGED_PATH = "/workspace/nietzche-sllm-project/ml/finetune/outputs/merged/epoch1"
EVAL_PATH = Path("/workspace/nietzche-sllm-project/ml/v2_data/sft_dataset/eval.jsonl")
BASELINE_RESPONSES = Path("/workspace/nietzche-sllm-project/ml/finetune/outputs/stage_b_test/test_a_baseline.jsonl")
OUT_PATH = Path("/workspace/nietzche-sllm-project/ml/finetune/outputs/stage_b_test/test_b2_epoch1.jsonl")

# 존재 확인
if not Path(MERGED_PATH).exists():
    raise FileNotFoundError(
        f"Merged model not found: {MERGED_PATH}\n"
        f"Run Test B-1 first."
    )

# ─────────────────────────────────────────────────────────
# 1. eval set 로드 (처음 5개만)
# ─────────────────────────────────────────────────────────
all_samples = [json.loads(l) for l in EVAL_PATH.open(encoding="utf-8")]
samples = all_samples[:5]  # 처음 5개만 테스트
print(f"\n[1] Loaded {len(samples)} eval samples (of {len(all_samples)} total)")

# baseline 응답 로드 (비교용)
baseline_map = {}
if BASELINE_RESPONSES.exists():
    for line in BASELINE_RESPONSES.open(encoding="utf-8"):
        r = json.loads(line)
        baseline_map[r["sample_id"]] = r["generated"]
    print(f"    Loaded {len(baseline_map)} baseline responses for comparison")

# ─────────────────────────────────────────────────────────
# 2. vLLM 로드
# ─────────────────────────────────────────────────────────
print(f"\n[2] Loading merged model into vLLM...")
print(f"    path: {MERGED_PATH}")
print(f"    max_model_len: 1280")
print(f"    enforce_eager: True")

t0 = time.time()
from vllm import LLM, SamplingParams

try:
    llm = LLM(
        model=MERGED_PATH,
        dtype="bfloat16",
        max_model_len=1280,  # prompt 400 + gen 768 + 여유
        enforce_eager=True,
        gpu_memory_utilization=0.90,
    )
    load_time = time.time() - t0
    print(f"    ✓ Load time: {load_time:.1f}s ({load_time/60:.1f} min)")
except Exception as e:
    print(f"    ✗ vLLM load FAILED: {type(e).__name__}: {e}")
    print(f"\n=== 리스크 B 발현 ===")
    print(f"peft merge는 성공했지만 vLLM이 못 읽음.")
    print(f"가능한 원인:")
    print(f"  - key 이름에 'base_model.model.' 접두사 남음")
    print(f"  - config.json의 architectures 불일치")
    print(f"  - safetensors metadata 이상")
    print(f"대안: Unsloth FastLanguageModel로 재merge 후 재시도")
    raise

# ─────────────────────────────────────────────────────────
# 3. Prompts 준비
# ─────────────────────────────────────────────────────────
print(f"\n[3] Building prompts...")
tokenizer = llm.get_tokenizer()
prompts = []
for s in samples:
    msgs = s["messages"][:2]
    prompt = tokenizer.apply_chat_template(
        msgs, tokenize=False, add_generation_prompt=True
    )
    prompts.append(prompt)
print(f"    ✓ Built {len(prompts)} prompts")

# ─────────────────────────────────────────────────────────
# 4. 생성
# ─────────────────────────────────────────────────────────
print(f"\n[4] Generating 5 responses (greedy, max_tokens=768)...")
sampling = SamplingParams(temperature=0.0, max_tokens=768)

t0 = time.time()
outputs = llm.generate(prompts, sampling)
gen_time = time.time() - t0
print(f"    ✓ Generation time: {gen_time:.1f}s")

# ─────────────────────────────────────────────────────────
# 5. 품질 확인 — baseline과 비교
# ─────────────────────────────────────────────────────────
print(f"\n[5] Quality check (epoch1 vs baseline comparison):")
print(f"{'=' * 60}")

for i, (s, out) in enumerate(zip(samples, outputs)):
    gen_text = out.outputs[0].text
    gen_tokens = len(out.outputs[0].token_ids)
    baseline_text = baseline_map.get(s["id"], "(baseline 없음)")
    
    print(f"\n--- Sample {i}: {s['id']} ---")
    print(f"Pattern: {s['response_pattern']} | Voice: {s['voice']} | Diff: {s['difficulty']}")
    print(f"USER: {s['messages'][1]['content'][:150]}")
    
    print(f"\n[BASELINE] {len(baseline_text)} chars")
    print(f"  {baseline_text[:400]}")
    if len(baseline_text) > 400:
        print(f"  ...")
    
    print(f"\n[EPOCH1] {len(gen_text)} chars, {gen_tokens} tokens")
    print(f"  {gen_text[:400]}")
    if len(gen_text) > 400:
        print(f"  ...")
    
    # 간단한 차이 지표
    diff_indicator = ""
    if baseline_text and len(baseline_text) > 0:
        len_ratio = len(gen_text) / len(baseline_text)
        if len_ratio < 0.7:
            diff_indicator = f"  ✓ epoch1이 더 짧음 (ratio {len_ratio:.2f}) — LoRA 효과 추정"
        elif len_ratio > 1.3:
            diff_indicator = f"  ⚠ epoch1이 더 김 (ratio {len_ratio:.2f})"
        else:
            diff_indicator = f"  · 비슷한 길이 (ratio {len_ratio:.2f})"
    print(diff_indicator)

# ─────────────────────────────────────────────────────────
# 6. 저장
# ─────────────────────────────────────────────────────────
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
with OUT_PATH.open("w", encoding="utf-8") as f:
    for s, out in zip(samples, outputs):
        record = {
            "sample_id": s["id"],
            "model_tag": "epoch1",
            "voice": s["voice"],
            "response_pattern": s["response_pattern"],
            "use_case": s["use_case"],
            "difficulty": s["difficulty"],
            "messages": s["messages"][:2],
            "reference": s["messages"][2]["content"],
            "generated": out.outputs[0].text,
            "gen_tokens": len(out.outputs[0].token_ids),
        }
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
print(f"\n[6] Saved to: {OUT_PATH}")

# ─────────────────────────────────────────────────────────
# 7. 요약
# ─────────────────────────────────────────────────────────
print(f"\n{'=' * 60}")
print(f"Test B-2 COMPLETE")
print(f"{'=' * 60}")
print(f"  vLLM load:  {load_time:.1f}s ({load_time/60:.1f} min)")
print(f"  Generation: {gen_time:.1f}s (5 samples)")
print(f"\n판단 기준:")
print(f"  1. 로드 성공? → 리스크 B 해결")
print(f"  2. 응답이 baseline과 다름? → 리스크 C 해결 (LoRA 실제 반영)")
print(f"  3. 응답이 짧아졌나? → 가설 검증 (LoRA가 길이 제어 학습)")
print(f"\n3개 모두 OK면 → Stage B 본 실행 진행 가능")
