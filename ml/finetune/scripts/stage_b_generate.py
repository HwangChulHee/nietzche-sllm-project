"""Stage B: Generate responses for a single model.

ml venv에서 실행. 한 모델만 로드해서 138 샘플 추론 후 종료.
- baseline: HF에서 google/gemma-4-31B-it
- epoch1~5: 로컬 merged 디렉토리

결과를 stage_b_responses.jsonl에 append (모델별 한 번씩 호출되어 점진적으로 채워짐).
이미 처리된 (sample_id, model_tag) 조합은 자동 skip → 중간 재시작 가능.

Usage:
    cd /workspace/nietzche-sllm-project/ml
    source .venv/bin/activate
    
    # baseline (HF에서 직접)
    python finetune/scripts/stage_b_generate.py \
        --model-tag baseline \
        --model-path google/gemma-4-31B-it
    
    # epoch (merged 로컬 경로)
    python finetune/scripts/stage_b_generate.py \
        --model-tag epoch2 \
        --model-path /workspace/.../finetune/outputs/merged/epoch2

환경:
    ml venv (vllm 0.19 + transformers 5.5 + torch 2.10)
"""
import argparse
import json
import sys
import time
from pathlib import Path


# ─────────────────────────────────────────────────────────
# 경로
# ─────────────────────────────────────────────────────────
EVAL_PATH = Path("/workspace/nietzche-sllm-project/ml/v2_data/sft_dataset/eval.jsonl")
OUTPUT_DIR = Path("/workspace/nietzche-sllm-project/ml/finetune/outputs/stage_b")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
RESPONSES_PATH = OUTPUT_DIR / "responses.jsonl"

# ─────────────────────────────────────────────────────────
# 추론 설정
# ─────────────────────────────────────────────────────────
MAX_MODEL_LEN = 1280   # prompt ~400 + gen 768 + 여유
MAX_NEW_TOKENS = 768
TEMPERATURE = 0.0      # greedy (Stage A와 결정 일치)
GPU_MEM_UTIL = 0.90


def load_eval_samples():
    samples = [json.loads(l) for l in EVAL_PATH.open(encoding="utf-8")]
    print(f"[gen] Loaded {len(samples)} eval samples")
    return samples


def load_already_done(model_tag: str) -> set:
    """이 모델 태그로 이미 처리된 sample_id 집합."""
    if not RESPONSES_PATH.exists():
        return set()
    done = set()
    with RESPONSES_PATH.open(encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
                if r.get("model_tag") == model_tag:
                    done.add(r["sample_id"])
            except json.JSONDecodeError:
                continue
    return done


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-tag", required=True,
                        help="baseline, epoch1, epoch2, ...")
    parser.add_argument("--model-path", required=True,
                        help="HF model id or local merged path")
    args = parser.parse_args()
    
    print("=" * 60)
    print(f"Stage B Generate: {args.model_tag}")
    print(f"  path: {args.model_path}")
    print("=" * 60)
    
    # ─────────────────────────────────────────────────────────
    # 1. 샘플 + resume 체크
    # ─────────────────────────────────────────────────────────
    samples = load_eval_samples()
    already_done = load_already_done(args.model_tag)
    if already_done:
        print(f"[gen] Already done: {len(already_done)} samples for {args.model_tag}")
        samples = [s for s in samples if s["id"] not in already_done]
        if not samples:
            print(f"[gen] All {args.model_tag} samples already done. Exiting.")
            return
        print(f"[gen] Remaining: {len(samples)} samples")
    
    # ─────────────────────────────────────────────────────────
    # 2. vLLM 로드
    # ─────────────────────────────────────────────────────────
    print(f"\n[gen] Loading vLLM...")
    print(f"  max_model_len:           {MAX_MODEL_LEN}")
    print(f"  enforce_eager:           True")
    print(f"  gpu_memory_utilization:  {GPU_MEM_UTIL}")
    
    t0 = time.time()
    from vllm import LLM, SamplingParams
    
    try:
        llm = LLM(
            model=args.model_path,
            dtype="bfloat16",
            max_model_len=MAX_MODEL_LEN,
            enforce_eager=True,
            gpu_memory_utilization=GPU_MEM_UTIL,
        )
    except Exception as e:
        print(f"[gen] vLLM load FAILED: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
    
    load_time = time.time() - t0
    print(f"[gen] Load time: {load_time:.1f}s ({load_time/60:.1f} min)")
    
    # ─────────────────────────────────────────────────────────
    # 3. Prompts 생성
    # ─────────────────────────────────────────────────────────
    print(f"\n[gen] Building prompts...")
    tokenizer = llm.get_tokenizer()
    prompts = []
    for s in samples:
        msgs = s["messages"][:2]  # system + user
        prompt = tokenizer.apply_chat_template(
            msgs,
            tokenize=False,
            add_generation_prompt=True,
        )
        prompts.append(prompt)
    print(f"[gen] Built {len(prompts)} prompts")
    
    # ─────────────────────────────────────────────────────────
    # 4. 생성
    # ─────────────────────────────────────────────────────────
    print(f"\n[gen] Generating {len(prompts)} responses (greedy, max_tokens={MAX_NEW_TOKENS})...")
    sampling = SamplingParams(
        temperature=TEMPERATURE,
        max_tokens=MAX_NEW_TOKENS,
    )
    
    t0 = time.time()
    outputs = llm.generate(prompts, sampling)
    gen_time = time.time() - t0
    print(f"[gen] Generation time: {gen_time:.1f}s ({gen_time/60:.1f} min)")
    print(f"[gen] Per-sample avg: {gen_time / len(prompts):.2f}s")
    
    # ─────────────────────────────────────────────────────────
    # 5. 결과 append
    # ─────────────────────────────────────────────────────────
    n_truncated = 0
    total_tokens = 0
    with RESPONSES_PATH.open("a", encoding="utf-8") as f:
        for s, out in zip(samples, outputs):
            gen_text = out.outputs[0].text
            gen_tokens = len(out.outputs[0].token_ids)
            total_tokens += gen_tokens
            if gen_tokens >= MAX_NEW_TOKENS:
                n_truncated += 1
            
            record = {
                "sample_id": s["id"],
                "model_tag": args.model_tag,
                "voice": s["voice"],
                "response_pattern": s["response_pattern"],
                "use_case": s["use_case"],
                "difficulty": s["difficulty"],
                "messages": s["messages"][:2],
                "reference": s["messages"][2]["content"],
                "generated": gen_text,
                "gen_tokens": gen_tokens,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    avg_tokens = total_tokens / len(outputs) if outputs else 0
    
    # ─────────────────────────────────────────────────────────
    # 6. 요약
    # ─────────────────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print(f"DONE: {args.model_tag}")
    print(f"{'=' * 60}")
    print(f"  vLLM load:    {load_time:>6.1f}s")
    print(f"  Generation:   {gen_time:>6.1f}s ({len(outputs)} samples)")
    print(f"  Total:        {load_time + gen_time:>6.1f}s")
    print(f"  Avg tokens:   {avg_tokens:.0f}")
    print(f"  Truncated:    {n_truncated}/{len(outputs)} ({n_truncated/len(outputs)*100:.0f}%)")
    print(f"  Output:       {RESPONSES_PATH}")


if __name__ == "__main__":
    main()
