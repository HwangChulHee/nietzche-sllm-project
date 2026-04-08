#!/bin/bash
#
# 05_warm_cache.sh — HuggingFace 모델 사전 다운로드 + 캐시 영구화
#
# RunPod의 /root는 Pod 재시작 시 휘발됨. /workspace는 네트워크 볼륨에 마운트되어 영구.
# 따라서 모델 캐시를 /workspace/.cache/huggingface로 옮기고,
# 자주 쓰는 모델들을 미리 받아두면 매번 재다운로드를 피할 수 있다.
#
# 다운로드 대상:
#   - intfloat/multilingual-e5-large (562MB) — Stage 4 임베딩
#   - Marker 모델들 (~2-3GB) — Stage 0.5 OCR
#
# 사용법:
#   bash scripts/setup/05_warm_cache.sh
#
# 환경변수:
#   HF_CACHE_DIR  — 캐시 경로 (기본: /workspace/.cache/huggingface)
#   SKIP_E5       — true면 e5 다운로드 스킵
#   SKIP_MARKER   — true면 marker 다운로드 스킵

set -e

HF_CACHE_DIR="${HF_CACHE_DIR:-/workspace/.cache/huggingface}"
SKIP_E5="${SKIP_E5:-false}"
SKIP_MARKER="${SKIP_MARKER:-false}"

echo "=========================================="
echo "  HuggingFace cache warming"
echo "=========================================="
echo "  Cache dir: $HF_CACHE_DIR"
echo ""

mkdir -p "$HF_CACHE_DIR"
export HF_HOME="$HF_CACHE_DIR"
export HUGGINGFACE_HUB_CACHE="$HF_CACHE_DIR/hub"
export TRANSFORMERS_CACHE="$HF_CACHE_DIR/hub"

# === 1. multilingual-e5-large (Stage 4 임베딩) ===
if [ "$SKIP_E5" != "true" ]; then
  echo ">>> Downloading intfloat/multilingual-e5-large..."
  python -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('intfloat/multilingual-e5-large')
print(f'  Loaded: {model.get_sentence_embedding_dimension()}d')
" || echo "  [WARN] e5 download failed (sentence-transformers not installed?)"
  echo ""
fi

# === 2. Marker 모델 (Stage 0.5 OCR) ===
if [ "$SKIP_MARKER" != "true" ]; then
  echo ">>> Downloading Marker models (Surya OCR + layout)..."
  python -c "
try:
    from marker.models import create_model_dict
    models = create_model_dict()
    print(f'  Loaded {len(models)} marker submodels')
except ImportError:
    print('  [WARN] marker-pdf not installed, skipping')
except Exception as e:
    print(f'  [WARN] marker model load failed: {e}')
"
  echo ""
fi

# === 3. 캐시 크기 확인 ===
echo ">>> Cache size:"
du -sh "$HF_CACHE_DIR" 2>/dev/null || echo "  (empty)"
echo ""

echo "✅ Cache warming done."
echo ""
echo "Tip: Add these to ~/.bashrc to persist HF_HOME across shell sessions:"
echo "  export HF_HOME=\"$HF_CACHE_DIR\""
echo "  export HUGGINGFACE_HUB_CACHE=\"$HF_CACHE_DIR/hub\""
echo ""
echo "Or run: bash scripts/setup/06_shell_init.sh"
