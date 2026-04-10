"""Test B-1: Merge epoch1 LoRA into Gemma 4 31B base using peft.

목적:
  리스크 A 검증 — peft가 Gemma 4 LoRA (Gemma4ClippableLinear 커스텀 레이어)를
  제대로 merge할 수 있는가?

환경:
  finetune venv (torch 2.6 + transformers 5.5 + peft 0.18 + unsloth 2026.4.4)
  ※ peft가 실패하면 Unsloth fallback 준비됨 (하단 주석 참고)

실행:
  cd /workspace/nietzche-sllm-project/ml/finetune
  source .venv/bin/activate
  python scripts/test_b1_merge_epoch1.py 2>&1 | tee logs/test_b1.log

성공 기준:
  - AutoModelForImageTextToText로 base 로드 성공
  - PeftModel.from_pretrained으로 adapter 로드 성공
  - merge_and_unload() 에러 없이 완료
  - save_pretrained으로 62GB 모델 저장 완료
  - 저장된 config.json이 원본과 동일한 model_type ("gemma4")

실패 시 대안:
  1. peft 경로 실패 → Unsloth FastLanguageModel.from_pretrained(checkpoint_path)
     .save_pretrained_merged() 사용. Unsloth는 학습 때 쓴 도구라 Gemma 4
     커스텀 레이어를 완벽히 앎.
  2. Unsloth도 실패 → 원래의 Unsloth 직접 추론 fallback (6시간)
"""
import gc
import time
from pathlib import Path

# Unsloth를 맨 먼저 import (패치 최적화 적용)
import unsloth  # noqa: F401

import torch

print("=" * 60)
print("Test B-1: Merge epoch1 LoRA into Gemma 4 31B base")
print("=" * 60)

# ─────────────────────────────────────────────────────────
# 경로
# ─────────────────────────────────────────────────────────
BASE_MODEL = "google/gemma-4-31B-it"
CHECKPOINT = "/workspace/nietzche-sllm-project/ml/finetune/outputs/nietzsche-lora-31b/checkpoint-144"
MERGED_OUT = "/workspace/nietzche-sllm-project/ml/finetune/outputs/merged/epoch1"

print(f"\n설정:")
print(f"  base:       {BASE_MODEL}")
print(f"  checkpoint: {CHECKPOINT}")
print(f"  output:     {MERGED_OUT}")

# 체크포인트 존재 확인
ckpt_path = Path(CHECKPOINT)
if not ckpt_path.exists():
    raise FileNotFoundError(f"Checkpoint not found: {CHECKPOINT}")

adapter_config = ckpt_path / "adapter_config.json"
adapter_weights = ckpt_path / "adapter_model.safetensors"
print(f"\n체크포인트 내용:")
print(f"  adapter_config.json: {'OK' if adapter_config.exists() else 'MISSING'}")
print(f"  adapter_model.safetensors: {'OK' if adapter_weights.exists() else 'MISSING'}")

# ─────────────────────────────────────────────────────────
# Step 1: base 모델 로드 (CPU)
# ─────────────────────────────────────────────────────────
print(f"\n[1] Loading base model (CPU, bf16)...")
print(f"    ※ CPU 로드는 GPU 메모리 안 씀. 시간은 걸리지만 안전.")
t0 = time.time()

from transformers import AutoModelForImageTextToText, AutoTokenizer

base = AutoModelForImageTextToText.from_pretrained(
    BASE_MODEL,
    torch_dtype=torch.bfloat16,
    device_map="cpu",
    low_cpu_mem_usage=True,
)
print(f"    ✓ Base loaded in {time.time() - t0:.1f}s")
print(f"    Model class: {type(base).__name__}")
print(f"    Num parameters: {sum(p.numel() for p in base.parameters()) / 1e9:.1f}B")

# ─────────────────────────────────────────────────────────
# Step 2: LoRA adapter 로드
# ─────────────────────────────────────────────────────────
print(f"\n[2] Loading LoRA adapter from checkpoint...")
t0 = time.time()

from peft import PeftModel

try:
    model = PeftModel.from_pretrained(base, CHECKPOINT)
    print(f"    ✓ Adapter loaded in {time.time() - t0:.1f}s")
    print(f"    Wrapped model class: {type(model).__name__}")
except Exception as e:
    print(f"    ✗ FAILED: {type(e).__name__}: {e}")
    print(f"\n=== peft 경로 실패 ===")
    print(f"Unsloth fallback으로 전환 필요:")
    print(f"  from unsloth import FastLanguageModel")
    print(f"  model, tok = FastLanguageModel.from_pretrained('{CHECKPOINT}', max_seq_length=1024)")
    print(f"  model.save_pretrained_merged('{MERGED_OUT}', tok)")
    raise

# ─────────────────────────────────────────────────────────
# Step 3: merge_and_unload()
# ─────────────────────────────────────────────────────────
print(f"\n[3] Merging adapter into base weights...")
print(f"    ※ 여기서 에러 나면 Gemma4ClippableLinear 호환성 문제")
t0 = time.time()

try:
    merged = model.merge_and_unload()
    print(f"    ✓ Merge completed in {time.time() - t0:.1f}s")
    print(f"    Merged model class: {type(merged).__name__}")
except Exception as e:
    print(f"    ✗ FAILED: {type(e).__name__}: {e}")
    print(f"\n=== merge 실패 ===")
    print(f"이건 정확히 예상했던 리스크 A입니다.")
    print(f"Unsloth fallback 경로로 재시도해야 합니다.")
    raise

# 메모리 정리 (중간 객체 제거)
del model
del base
gc.collect()

# ─────────────────────────────────────────────────────────
# Step 4: save_pretrained
# ─────────────────────────────────────────────────────────
print(f"\n[4] Saving merged model to {MERGED_OUT}...")
print(f"    ※ 62GB 저장. 네트워크 FS라 시간 걸림.")
t0 = time.time()

Path(MERGED_OUT).mkdir(parents=True, exist_ok=True)

try:
    merged.save_pretrained(
        MERGED_OUT,
        safe_serialization=True,
        max_shard_size="10GB",
    )
    print(f"    ✓ Model saved in {time.time() - t0:.1f}s")
except Exception as e:
    print(f"    ✗ FAILED: {type(e).__name__}: {e}")
    raise

# Tokenizer도 같이 저장 (vLLM이 필요로 함)
print(f"\n[5] Saving tokenizer...")
tok = AutoTokenizer.from_pretrained(BASE_MODEL)
tok.save_pretrained(MERGED_OUT)
print(f"    ✓ Tokenizer saved")

# ─────────────────────────────────────────────────────────
# Step 6: 저장된 파일 검증
# ─────────────────────────────────────────────────────────
print(f"\n[6] Verifying saved files...")
import os
import json

total_size = 0
file_count = 0
safetensor_count = 0
for f in os.listdir(MERGED_OUT):
    fp = os.path.join(MERGED_OUT, f)
    if os.path.isfile(fp):
        size = os.path.getsize(fp)
        total_size += size
        file_count += 1
        if f.endswith(".safetensors"):
            safetensor_count += 1

print(f"    Files: {file_count} ({safetensor_count} safetensors)")
print(f"    Total size: {total_size / 1e9:.1f} GB")

# config.json 확인
config_path = os.path.join(MERGED_OUT, "config.json")
if os.path.exists(config_path):
    with open(config_path) as f:
        cfg = json.load(f)
    print(f"    model_type: {cfg.get('model_type', 'MISSING')}")
    arch = cfg.get('architectures', ['UNKNOWN'])
    print(f"    architectures: {arch}")
    if cfg.get('model_type') == 'gemma4':
        print(f"    ✓ Config looks correct for vLLM loading")
    else:
        print(f"    ⚠ model_type이 'gemma4'가 아님 — vLLM 로드 실패 가능")
else:
    print(f"    ✗ config.json MISSING")

# peft 흔적 확인 (있으면 vLLM 로드 실패 가능)
peft_files = [f for f in os.listdir(MERGED_OUT) if 'adapter' in f.lower() or 'peft' in f.lower()]
if peft_files:
    print(f"    ⚠ peft 관련 파일 발견: {peft_files}")
    print(f"      (vLLM이 이 파일들을 무시하면 괜찮음)")

# ─────────────────────────────────────────────────────────
# 요약
# ─────────────────────────────────────────────────────────
print(f"\n{'=' * 60}")
print(f"Test B-1 COMPLETE")
print(f"{'=' * 60}")
print(f"다음 단계: Test B-2 (vLLM으로 merged model 로드 테스트)")
print(f"  cd /workspace/nietzche-sllm-project/ml")
print(f"  source .venv/bin/activate")
print(f"  python finetune/scripts/test_b2_vllm_merged.py")
