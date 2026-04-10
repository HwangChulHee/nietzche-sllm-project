"""
Stage B - Step 1: Generate responses from each model variant.

Loads base model once (HF transformers), swaps LoRA adapters via peft.
Generates responses for a random subset of held-out test set.

Output: responses.jsonl with one record per (model_tag, sample).

Run:
    cd /workspace/nietzche-sllm-project/ml/finetune
    poetry run python scripts/stage_b_generate.py
"""
import json
import random
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# ---------- paths ----------
ROOT = Path(__file__).resolve().parent.parent  # finetune/
EVAL_PATH = Path("/workspace/nietzche-sllm-project/ml/v2_data/sft_dataset/eval.jsonl")
OUTPUT_DIR = ROOT / "outputs" / "stage_b"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
RESPONSES_PATH = OUTPUT_DIR / "responses.jsonl"

LORA_RUN_DIR = ROOT / "outputs" / "nietzsche-lora-31b"

# ---------- config ----------
BASE_MODEL = "google/gemma-4-31B-it"
MAX_NEW_TOKENS = 256
TEMPERATURE = 0.7
TOP_P = 0.9
SEED = 42
N_SAMPLES = 100

# ---------- checkpoints ----------
CHECKPOINTS = {
    "baseline": None,
    "epoch1":   LORA_RUN_DIR / "checkpoint-144",
    "epoch2":   LORA_RUN_DIR / "checkpoint-288",
    "epoch3":   LORA_RUN_DIR / "checkpoint-432",
    "epoch4":   LORA_RUN_DIR / "checkpoint-576",
    "epoch5":   LORA_RUN_DIR / "checkpoint-720",
}

ADAPTER_NAME = "nietzsche"

# ---------- load eval data (random sample, fixed seed) ----------
def load_eval_samples():
    with open(EVAL_PATH) as f:
        all_rows = [json.loads(l) for l in f]

    rng = random.Random(SEED)
    rng.shuffle(all_rows)
    selected = all_rows[:N_SAMPLES]

    samples = []
    for row in selected:
        input_msgs = [m for m in row["messages"] if m["role"] != "assistant"]
        reference = next(m["content"] for m in row["messages"] if m["role"] == "assistant")
        samples.append({
            "sample_id": row["id"],
            "input_messages": input_msgs,
            "reference": reference,
        })
    return samples

# ---------- generate ----------
def generate_response(model, tokenizer, input_messages, sample_seed):
    # 모델 간 공정 비교를 위해 샘플마다 같은 seed 재설정
    torch.manual_seed(sample_seed)
    torch.cuda.manual_seed_all(sample_seed)

    prompt = tokenizer.apply_chat_template(
        input_messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    t0 = time.time()
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            temperature=TEMPERATURE,
            top_p=TOP_P,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )
    elapsed = time.time() - t0

    generated_tokens = outputs[0][inputs["input_ids"].shape[1]:]
    response = tokenizer.decode(generated_tokens, skip_special_tokens=True)
    return response.strip(), elapsed

# ---------- run one model ----------
def run_model_on_samples(model, tokenizer, samples, model_tag, fout):
    print(f"\n{'=' * 60}")
    print(f"Generating responses: {model_tag}")
    print(f"{'=' * 60}")

    errors = 0
    for i, sample in enumerate(samples):
        # sample_seed는 SEED + index로 결정. 모델 간에 같은 sample_id는 같은 seed.
        sample_seed = SEED + i
        try:
            response, elapsed = generate_response(
                model, tokenizer, sample["input_messages"], sample_seed
            )
        except Exception as e:
            print(f"  [ERROR] sample {i}: {e}")
            response = f"[ERROR: {type(e).__name__}: {str(e)[:100]}]"
            elapsed = 0.0
            errors += 1

        record = {
            "sample_id": sample["sample_id"],
            "model_tag": model_tag,
            "input_messages": sample["input_messages"],
            "reference": sample["reference"],
            "generated": response,
            "gen_time_sec": round(elapsed, 2),
        }
        fout.write(json.dumps(record, ensure_ascii=False) + "\n")
        fout.flush()

        if (i + 1) % 10 == 0:
            print(f"  [{i+1}/{len(samples)}] last gen: {elapsed:.1f}s")

    if errors:
        print(f"  ({errors} errors out of {len(samples)})")

# ---------- main ----------
def main():
    samples = load_eval_samples()
    print(f"Loaded {len(samples)} eval samples (random sample, seed={SEED})")
    print(f"Will generate responses for {len(CHECKPOINTS)} models")
    print(f"Total generations: {len(samples) * len(CHECKPOINTS)}")
    print()

    # 기존 결과 백업
    if RESPONSES_PATH.exists():
        backup = RESPONSES_PATH.with_suffix(".jsonl.bak")
        RESPONSES_PATH.rename(backup)
        print(f"Backed up existing responses to: {backup}")

    # ---------- Base model 1회 로드 (transformers 직접) ----------
    print("=" * 60)
    print(f"Loading base model: {BASE_MODEL}")
    print("=" * 60)
    t0 = time.time()
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )
    base_model.eval()
    print(f"Base model loaded in {time.time() - t0:.1f}s\n")

    fout = open(RESPONSES_PATH, "a")

    # ---------- 1. Baseline (LoRA 없음) ----------
    run_model_on_samples(base_model, tokenizer, samples, "baseline", fout)

    # ---------- 2. LoRA 체크포인트들 ----------
    peft_model = None
    for model_tag, ckpt_path in CHECKPOINTS.items():
        if ckpt_path is None:
            continue
        if not ckpt_path.exists():
            print(f"\n[SKIP] {model_tag}: checkpoint not found at {ckpt_path}")
            continue

        print(f"\nLoading adapter: {ckpt_path}")
        t0 = time.time()

        if peft_model is None:
            # 첫 LoRA — PeftModel로 wrap
            peft_model = PeftModel.from_pretrained(
                base_model,
                str(ckpt_path),
                adapter_name=ADAPTER_NAME,
            )
            peft_model.eval()
        else:
            # 두 번째부터는 어댑터만 교체
            peft_model.delete_adapter(ADAPTER_NAME)
            peft_model.load_adapter(str(ckpt_path), adapter_name=ADAPTER_NAME)

        peft_model.set_adapter(ADAPTER_NAME)
        print(f"  Adapter loaded in {time.time() - t0:.1f}s")

        run_model_on_samples(peft_model, tokenizer, samples, model_tag, fout)

    fout.close()

    print(f"\n{'=' * 60}")
    print(f"All done. Responses saved to: {RESPONSES_PATH}")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()