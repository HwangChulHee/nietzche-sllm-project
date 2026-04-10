"""Test B-1 v2: Merge epoch1 LoRA using Unsloth (peft 실패 대안).

v1 (peft 경로)이 Gemma4ClippableLinear 커스텀 레이어를 못 인식해서 실패.
Unsloth는 학습 때 쓴 도구라 이 레이어를 완벽히 앎.

전략:
  Unsloth FastLanguageModel.from_pretrained()에 checkpoint 경로를 직접 넘김.
  Unsloth가 adapter_config.json을 읽어 base + adapter를 자동 로드.
  save_pretrained_merged()로 full merged model 저장.

환경:
  finetune venv (unsloth 2026.4.4 + torch 2.6 + peft 0.18)

실행:
  cd /workspace/nietzche-sllm-project/ml/finetune
  source .venv/bin/activate
  python scripts/test_b1_merge_epoch1_unsloth.py 2>&1 | tee logs/test_b1_unsloth.log

성공 기준:
  - Unsloth가 checkpoint 로드 성공 (base + adapter)
  - save_pretrained_merged() 에러 없이 완료
  - /workspace/.../merged/epoch1/ 에 62GB 모델 저장
  - config.json의 model_type = "gemma4"

참고:
  - Unsloth의 save_pretrained_merged는 내부적으로 merge를 처리
  - save_method="merged_16bit" (bf16으로 병합, 기본값)
"""
import gc
import time
from pathlib import Path

# Unsloth 최우선 import
from unsloth import FastLanguageModel

import torch

print("=" * 60)
print("Test B-1 v2: Merge epoch1 LoRA using Unsloth")
print("=" * 60)

# ─────────────────────────────────────────────────────────
# 경로
# ─────────────────────────────────────────────────────────
CHECKPOINT = "/workspace/nietzche-sllm-project/ml/finetune/outputs/nietzsche-lora-31b/checkpoint-144"
MERGED_OUT = "/workspace/nietzche-sllm-project/ml/finetune/outputs/merged/epoch1"
MAX_SEQ_LEN = 1024  # 추론용이라 작게 (학습 때는 384였음, 추론은 1024면 충분)

print(f"\n설정:")
print(f"  checkpoint: {CHECKPOINT}")
print(f"  output:     {MERGED_OUT}")
print(f"  max_seq_len: {MAX_SEQ_LEN}")

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
# Step 1: Unsloth로 base + adapter 로드
# ─────────────────────────────────────────────────────────
print(f"\n[1] Loading base + adapter via Unsloth FastLanguageModel...")
print(f"    ※ Unsloth가 adapter_config.json을 읽어 base를 자동 fetch")
t0 = time.time()

try:
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=CHECKPOINT,
        max_seq_length=MAX_SEQ_LEN,
        dtype=None,  # auto bf16 on A100
        load_in_4bit=False,  # bf16 full, not quantized
    )
    print(f"    ✓ Loaded in {time.time() - t0:.1f}s")
    print(f"    Model class: {type(model).__name__}")
except Exception as e:
    print(f"    ✗ FAILED: {type(e).__name__}: {e}")
    print(f"\n=== Unsloth 로드 실패 ===")
    print(f"이건 심각합니다 — 학습 때 쓴 도구가 자기 결과물을 못 읽음")
    raise

# ─────────────────────────────────────────────────────────
# Step 2: save_pretrained_merged
# ─────────────────────────────────────────────────────────
print(f"\n[2] Merging and saving with save_pretrained_merged...")
print(f"    ※ 62GB 저장. 네트워크 FS 쓰기라 5분 이상 걸릴 수 있음.")
t0 = time.time()

Path(MERGED_OUT).mkdir(parents=True, exist_ok=True)

try:
    # save_method:
    #   "merged_16bit" = bf16 merged full model (권장, vLLM 호환)
    #   "merged_4bit" = 4bit quantized merged (우리는 fp8 배포라 불필요)
    #   "lora" = adapter만 저장 (우리는 merged 원함)
    model.save_pretrained_merged(
        MERGED_OUT,
        tokenizer,
        save_method="merged_16bit",
    )
    print(f"    ✓ Save completed in {time.time() - t0:.1f}s")
except Exception as e:
    print(f"    ✗ FAILED: {type(e).__name__}: {e}")
    raise

# 메모리 정리
del model
del tokenizer
gc.collect()
if torch.cuda.is_available():
    torch.cuda.empty_cache()

# ─────────────────────────────────────────────────────────
# Step 3: 저장된 파일 검증
# ─────────────────────────────────────────────────────────
print(f"\n[3] Verifying saved files...")
import os
import json

total_size = 0
file_count = 0
safetensor_count = 0
files_list = []
for f in sorted(os.listdir(MERGED_OUT)):
    fp = os.path.join(MERGED_OUT, f)
    if os.path.isfile(fp):
        size = os.path.getsize(fp)
        total_size += size
        file_count += 1
        files_list.append((f, size))
        if f.endswith(".safetensors"):
            safetensor_count += 1

print(f"    Files: {file_count} ({safetensor_count} safetensors)")
print(f"    Total size: {total_size / 1e9:.1f} GB")

# 파일 목록 (큰 순)
print(f"\n    Top files by size:")
for f, s in sorted(files_list, key=lambda x: -x[1])[:10]:
    print(f"      {s/1e9:>6.2f} GB  {f}")

# config.json 확인
config_path = os.path.join(MERGED_OUT, "config.json")
if os.path.exists(config_path):
    with open(config_path) as f:
        cfg = json.load(f)
    mt = cfg.get('model_type', 'MISSING')
    arch = cfg.get('architectures', ['UNKNOWN'])
    print(f"\n    config.json:")
    print(f"      model_type: {mt}")
    print(f"      architectures: {arch}")
    if mt == 'gemma4':
        print(f"      ✓ Config OK for vLLM")
    else:
        print(f"      ⚠ model_type 이상 — vLLM 로드 실패 가능")
else:
    print(f"\n    ✗ config.json MISSING")

# peft 흔적 확인
peft_files = [f for f, _ in files_list if 'adapter' in f.lower() or 'peft' in f.lower()]
if peft_files:
    print(f"\n    ⚠ peft 관련 파일 발견: {peft_files}")
    print(f"      (vLLM이 무시하면 OK. 문제시 수동 삭제)")

# tokenizer 확인
tok_files = [f for f, _ in files_list if 'tokenizer' in f.lower() or f == 'special_tokens_map.json']
print(f"\n    Tokenizer files: {len(tok_files)}")
for f in tok_files:
    print(f"      {f}")

# ─────────────────────────────────────────────────────────
# 요약
# ─────────────────────────────────────────────────────────
print(f"\n{'=' * 60}")
print(f"Test B-1 v2 COMPLETE")
print(f"{'=' * 60}")
print(f"다음 단계: Test B-2 (vLLM으로 merged model 로드)")
print(f"  새 터미널 열고:")
print(f"  cd /workspace/nietzche-sllm-project/ml")
print(f"  source .venv/bin/activate")
print(f"  python finetune/scripts/test_b2_vllm_merged.py")
