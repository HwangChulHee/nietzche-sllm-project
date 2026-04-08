#!/bin/bash
#
# 08_warm_llm.sh — vLLM 서빙용 LLM 모델 사전 다운로드
#
# 다운로드 대상 (BF16, 약 115GB):
#   - google/gemma-4-26B-A4B-it (~52GB, MoE, 4B active params, 빠름)
#   - google/gemma-4-31B-it     (~62GB, Dense, 품질 위)
#
# 둘 다 A100 80GB에서 BF16으로 추론 가능.
# 4090에서는 4-bit 양자화 필요 (DOWNLOAD_AWQ=true 옵션).
#
# 캐시는 /workspace에 영구화되므로 4090 → A100 Pod 마이그레이션 시
# 다시 다운로드 안 해도 됨.
#
# 사용법:
#   bash scripts/setup/08_warm_llm.sh
#
# 환경변수:
#   HF_CACHE_DIR    — HF 캐시 경로 (기본: /workspace/.cache/huggingface)
#   VLLM_CACHE_DIR  — vLLM 캐시 경로 (기본: /workspace/.cache/vllm)
#   HF_TOKEN        — HuggingFace 토큰 (Gemma 라이선스 동의 후 필요)
#   DOWNLOAD_AWQ    — true면 4-bit AWQ 버전 추가 다운로드 (4090용)
#   SKIP_DISK_CHECK — true면 디스크 공간 체크 스킵
#   MIN_DISK_GB     — 최소 디스크 여유 (기본: 130GB)

set -e

# === Configuration ===
HF_CACHE_DIR="${HF_CACHE_DIR:-/workspace/.cache/huggingface}"
VLLM_CACHE_DIR="${VLLM_CACHE_DIR:-/workspace/.cache/vllm}"
DOWNLOAD_AWQ="${DOWNLOAD_AWQ:-false}"
SKIP_DISK_CHECK="${SKIP_DISK_CHECK:-false}"
MIN_DISK_GB="${MIN_DISK_GB:-130}"

MODELS_BF16=(
  "google/gemma-4-26B-A4B-it"
  "google/gemma-4-31B-it"
)

# 4090용 4-bit AWQ (vLLM 호환 — community quant)
MODELS_AWQ=(
  "cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit"
)

echo "=========================================="
echo "  vLLM model warming (Gemma 4)"
echo "=========================================="
echo "  HF cache:    $HF_CACHE_DIR"
echo "  vLLM cache:  $VLLM_CACHE_DIR"
echo "  BF16 models: ${#MODELS_BF16[@]}"
if [ "$DOWNLOAD_AWQ" = "true" ]; then
  echo "  AWQ models:  ${#MODELS_AWQ[@]}"
fi
echo ""

# === 1. Disk space check ===
if [ "$SKIP_DISK_CHECK" != "true" ]; then
  echo ">>> Checking disk space on /workspace..."
  WS_AVAIL_GB=$(df -BG /workspace 2>/dev/null | awk 'NR==2 {gsub("G",""); print $4}')
  if [ -z "$WS_AVAIL_GB" ]; then
    echo "  [WARN] Could not check /workspace (not mounted?)"
  elif [ "$WS_AVAIL_GB" -lt "$MIN_DISK_GB" ]; then
    echo "  ❌ Insufficient disk: ${WS_AVAIL_GB}GB available, need ${MIN_DISK_GB}GB"
    echo ""
    echo "  Options:"
    echo "    1. Free up space in /workspace"
    echo "    2. Download only one model: edit MODELS_BF16 in this script"
    echo "    3. Skip this check: SKIP_DISK_CHECK=true bash $0"
    exit 1
  else
    echo "  ✅ ${WS_AVAIL_GB}GB available (need ${MIN_DISK_GB}GB)"
  fi
  echo ""
fi

# === 2. HF token check ===
echo ">>> Checking HuggingFace token..."
if [ -z "$HF_TOKEN" ] && [ ! -f "$HOME/.cache/huggingface/token" ]; then
  echo "  [WARN] HF_TOKEN not set and no cached token found."
  echo ""
  echo "  Gemma models may require license acceptance:"
  echo "    1. Visit https://huggingface.co/google/gemma-4-26B-A4B-it"
  echo "    2. Click 'Acknowledge license' (one-time)"
  echo "    3. Run: huggingface-cli login"
  echo ""
  echo "  If models are public for your account, you can ignore this."
  echo ""
  read -p "  Continue anyway? [y/N] " -n 1 -r
  echo ""
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
  fi
else
  echo "  ✅ Token available"
fi
echo ""

# === 3. transformers version check (vLLM Gemma 4 needs >= 5.5.0) ===
echo ">>> Checking transformers version..."
TRANSFORMERS_OK=$(python -c "
import sys
try:
    import transformers
    v = transformers.__version__
    parts = v.split('.')
    major = int(parts[0])
    minor = int(parts[1])
    if major > 5 or (major == 5 and minor >= 5):
        print(f'OK {v}')
    else:
        print(f'OLD {v}')
except ImportError:
    print('MISSING')
" 2>/dev/null)

case "$TRANSFORMERS_OK" in
  OK*)
    echo "  ✅ ${TRANSFORMERS_OK#OK }"
    ;;
  OLD*)
    echo "  ⚠️  ${TRANSFORMERS_OK#OLD } too old (need >= 5.5.0)"
    echo "  Installing newer transformers..."
    pip install -q -U 'transformers>=5.5.0'
    echo "  ✅ updated"
    ;;
  MISSING)
    echo "  ⚠️  transformers not installed, installing..."
    pip install -q 'transformers>=5.5.0'
    echo "  ✅ installed"
    ;;
esac
echo ""

# === 4. Setup cache paths ===
echo ">>> Setting up cache directories..."
mkdir -p "$HF_CACHE_DIR" "$VLLM_CACHE_DIR"
export HF_HOME="$HF_CACHE_DIR"
export HUGGINGFACE_HUB_CACHE="$HF_CACHE_DIR/hub"
export TRANSFORMERS_CACHE="$HF_CACHE_DIR/hub"
export VLLM_CACHE_ROOT="$VLLM_CACHE_DIR"

# Faster downloads if hf_transfer is available
pip install -q hf_transfer huggingface_hub 2>/dev/null || true
export HF_HUB_ENABLE_HF_TRANSFER=1
echo "  ✅ Cache paths set"
echo ""

# === 5. Download BF16 models ===
echo ">>> Downloading BF16 models..."
for model in "${MODELS_BF16[@]}"; do
  echo ""
  echo "  [$(date +%H:%M:%S)] $model"
  if huggingface-cli download "$model" 2>&1 | tail -5; then
    echo "  ✅ done"
  else
    echo "  ❌ FAILED: $model"
    echo ""
    echo "  Common causes:"
    echo "    - License not accepted: visit https://huggingface.co/$model"
    echo "    - Network issue: retry the script"
    echo "    - HF_TOKEN missing or invalid"
    exit 1
  fi
done
echo ""

# === 6. Optional AWQ download (4090용) ===
if [ "$DOWNLOAD_AWQ" = "true" ]; then
  echo ">>> Downloading 4-bit AWQ models (for 4090)..."
  for model in "${MODELS_AWQ[@]}"; do
    echo ""
    echo "  [$(date +%H:%M:%S)] $model"
    if huggingface-cli download "$model" 2>&1 | tail -5; then
      echo "  ✅ done"
    else
      echo "  ⚠️  FAILED (community quant may be unstable): $model"
    fi
  done
  echo ""
fi

# === 7. Verify ===
echo ">>> Cache size:"
du -sh "$HF_CACHE_DIR" 2>/dev/null
echo ""

echo ">>> Cached Gemma models:"
ls -d "$HF_CACHE_DIR/hub/models--google--gemma-4-"* 2>/dev/null | while read d; do
  size=$(du -sh "$d" | cut -f1)
  name=$(basename "$d" | sed 's/models--/  /; s/--/\//g')
  echo "  $name ($size)"
done
echo ""

# === 8. Done ===
echo "=========================================="
echo "  ✅ Done"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Add VLLM_CACHE_ROOT to your shell:"
echo "       bash scripts/setup/06_shell_init.sh"
echo "       source ~/.bashrc"
echo ""
echo "  2. Test serving (when ready):"
echo "       vllm serve google/gemma-4-26B-A4B-it \\"
echo "         --max-model-len 32768 \\"
echo "         --gpu-memory-utilization 0.90"
echo ""
echo "  3. Or 31B Dense:"
echo "       vllm serve google/gemma-4-31B-it \\"
echo "         --max-model-len 32768 \\"
echo "         --gpu-memory-utilization 0.90"
