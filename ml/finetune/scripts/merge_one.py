"""Merge single epoch's LoRA into Gemma 4 base using Unsloth.

stage_b_generate.py에서 subprocess로 호출되거나, 단독 실행 가능.

Usage:
    cd /workspace/nietzche-sllm-project/ml/finetune
    source .venv/bin/activate
    python scripts/merge_one.py --epoch 2

Output:
    /workspace/.../finetune/outputs/merged/epoch{N}/  (62GB)

환경:
    finetune venv (unsloth 2026.4.4 + torch 2.6 + peft 0.18)
"""
import argparse
import gc
import sys
import time
from pathlib import Path

# Unsloth 최우선 import
from unsloth import FastLanguageModel
import torch


CHECKPOINT_MAP = {
    1: "checkpoint-144",
    2: "checkpoint-288",
    3: "checkpoint-432",
    4: "checkpoint-576",
    5: "checkpoint-720",
}

LORA_RUN_DIR = Path("/workspace/nietzche-sllm-project/ml/finetune/outputs/nietzsche-lora-31b")
MERGED_BASE = Path("/workspace/nietzche-sllm-project/ml/finetune/outputs/merged")
MAX_SEQ_LEN = 1024


def merge_epoch(epoch: int) -> Path:
    if epoch not in CHECKPOINT_MAP:
        raise ValueError(f"Invalid epoch {epoch}. Must be one of {list(CHECKPOINT_MAP)}")
    
    ckpt_name = CHECKPOINT_MAP[epoch]
    checkpoint = LORA_RUN_DIR / ckpt_name
    output = MERGED_BASE / f"epoch{epoch}"
    
    if not checkpoint.exists():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint}")
    
    if output.exists() and any(output.iterdir()):
        print(f"[merge_one] epoch{epoch} already merged at {output}, SKIPPING")
        return output
    
    print(f"[merge_one] === Merging epoch{epoch} ===")
    print(f"[merge_one] checkpoint: {checkpoint}")
    print(f"[merge_one] output:     {output}")
    
    # ─────────────────────────────────────────────────────────
    # 1. Unsloth로 base + adapter 로드
    # ─────────────────────────────────────────────────────────
    print(f"[merge_one] [1/3] Loading base + adapter via Unsloth...")
    t0 = time.time()
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=str(checkpoint),
        max_seq_length=MAX_SEQ_LEN,
        dtype=None,
        load_in_4bit=False,
    )
    print(f"[merge_one] [1/3] Loaded in {time.time() - t0:.1f}s")
    
    # ─────────────────────────────────────────────────────────
    # 2. save_pretrained_merged
    # ─────────────────────────────────────────────────────────
    print(f"[merge_one] [2/3] Merging and saving...")
    t0 = time.time()
    output.mkdir(parents=True, exist_ok=True)
    model.save_pretrained_merged(
        str(output),
        tokenizer,
        save_method="merged_16bit",
    )
    print(f"[merge_one] [2/3] Save completed in {time.time() - t0:.1f}s")
    
    # ─────────────────────────────────────────────────────────
    # 3. 정리
    # ─────────────────────────────────────────────────────────
    del model
    del tokenizer
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    
    # 검증
    safetensors = list(output.glob("*.safetensors"))
    config = output / "config.json"
    if not safetensors or not config.exists():
        raise RuntimeError(f"Merge incomplete: missing files in {output}")
    
    total_size = sum(f.stat().st_size for f in output.iterdir() if f.is_file())
    print(f"[merge_one] [3/3] OK — {len(safetensors)} safetensors, {total_size / 1e9:.1f} GB total")
    print(f"[merge_one] === epoch{epoch} merge complete ===")
    
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epoch", type=int, required=True, choices=[1, 2, 3, 4, 5])
    args = parser.parse_args()
    
    try:
        out = merge_epoch(args.epoch)
        print(f"\nSUCCESS: {out}")
        sys.exit(0)
    except Exception as e:
        print(f"\nFAILED: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
