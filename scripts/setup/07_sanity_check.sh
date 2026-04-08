#!/bin/bash
#
# 07_sanity_check.sh — Pod 재시작 후 30초 안에 환경/데이터 무결성 확인
#
# 체크 항목:
#   1. Python + venv 정상
#   2. 핵심 패키지 임포트 가능
#   3. GPU 인식
#   4. HF 캐시 + 모델 (e5, marker, gemma 4)
#   5. vLLM 캐시
#   6. 데이터 파일들 존재
#
# 사용법:
#   bash scripts/setup/07_sanity_check.sh

PROJECT_DIR="${PROJECT_DIR:-/workspace/nietzche-sllm-project/ml}"
cd "$PROJECT_DIR" 2>/dev/null || { echo "❌ $PROJECT_DIR not found"; exit 1; }

echo "=========================================="
echo "  Sanity check"
echo "=========================================="
echo ""

PASS=0
FAIL=0

check() {
  local label="$1"
  local cmd="$2"
  if eval "$cmd" > /dev/null 2>&1; then
    echo "  ✅ $label"
    PASS=$((PASS + 1))
  else
    echo "  ❌ $label"
    FAIL=$((FAIL + 1))
  fi
}

# === 1. Environment ===
echo ">>> Environment"
check "Python 3.12+" "python --version | grep -E 'Python 3\.(1[2-9]|[2-9][0-9])'"
check "Virtual env active" "[ -n \"\$VIRTUAL_ENV\" ]"
check "Poetry installed" "command -v poetry"
echo ""

# === 2. Core packages ===
echo ">>> Core packages"
check "pydantic" "python -c 'import pydantic'"
check "rich" "python -c 'import rich'"
check "sentence-transformers" "python -c 'import sentence_transformers'"
check "torch + CUDA" "python -c 'import torch; assert torch.cuda.is_available()'"
check "marker-pdf" "python -c 'import marker'"
check "kss" "python -c 'import kss'"
check "pysbd" "python -c 'import pysbd'"
check "transformers >= 5.5.0" "python -c 'import transformers; v=transformers.__version__.split(\".\"); assert int(v[0])>5 or (int(v[0])==5 and int(v[1])>=5)'"
check "vllm" "python -c 'import vllm'"
echo ""

# === 3. GPU ===
echo ">>> GPU"
if command -v nvidia-smi > /dev/null 2>&1; then
  GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)
  GPU_MEM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader | head -1)
  echo "  ✅ GPU: $GPU_NAME ($GPU_MEM)"
  PASS=$((PASS + 1))
else
  echo "  ⚠️  no nvidia-smi (CPU only)"
fi
echo ""

# === 4. HF Cache ===
echo ">>> HuggingFace cache"
HF_DIR="${HF_HOME:-$HOME/.cache/huggingface}"
if [ -d "$HF_DIR" ]; then
  SIZE=$(du -sh "$HF_DIR" 2>/dev/null | cut -f1)
  echo "  ✅ HF_HOME: $HF_DIR ($SIZE)"
  PASS=$((PASS + 1))
else
  echo "  ⚠️  HF_HOME not set or empty: $HF_DIR"
fi

# Embedding model
E5_PATH="$HF_DIR/hub/models--intfloat--multilingual-e5-large"
if [ -d "$E5_PATH" ]; then
  echo "  ✅ multilingual-e5-large cached"
  PASS=$((PASS + 1))
else
  echo "  ⚠️  multilingual-e5-large NOT cached (run 05_warm_cache.sh)"
fi

# Gemma 4 26B A4B
GEMMA_26B="$HF_DIR/hub/models--google--gemma-4-26B-A4B-it"
if [ -d "$GEMMA_26B" ]; then
  GEMMA_26B_SIZE=$(du -sh "$GEMMA_26B" | cut -f1)
  echo "  ✅ gemma-4-26B-A4B-it cached ($GEMMA_26B_SIZE)"
  PASS=$((PASS + 1))
else
  echo "  ⚠️  gemma-4-26B-A4B-it NOT cached (run 08_warm_llm.sh)"
fi

# Gemma 4 31B
GEMMA_31B="$HF_DIR/hub/models--google--gemma-4-31B-it"
if [ -d "$GEMMA_31B" ]; then
  GEMMA_31B_SIZE=$(du -sh "$GEMMA_31B" | cut -f1)
  echo "  ✅ gemma-4-31B-it cached ($GEMMA_31B_SIZE)"
  PASS=$((PASS + 1))
else
  echo "  ⚠️  gemma-4-31B-it NOT cached (run 08_warm_llm.sh)"
fi
echo ""

# === 5. vLLM cache ===
echo ">>> vLLM cache"
VLLM_DIR="${VLLM_CACHE_ROOT:-$HOME/.cache/vllm}"
if [ -d "$VLLM_DIR" ]; then
  VLLM_SIZE=$(du -sh "$VLLM_DIR" 2>/dev/null | cut -f1)
  echo "  ✅ VLLM_CACHE_ROOT: $VLLM_DIR ($VLLM_SIZE)"
  PASS=$((PASS + 1))
else
  echo "  ⚠️  VLLM_CACHE_ROOT not set or empty: $VLLM_DIR"
fi
echo ""

# === 6. Pipeline data files ===
echo ">>> Pipeline data files"
declare -A FILES=(
  ["Stage 0 (PDF)"]="data/raw/joyful_science_extracted.pdf"
  ["Marker JSON"]="data/marker_output/joyful_science_extracted/joyful_science_extracted.json"
  ["Stage 1 (pages)"]="data/extracted/joyful_science_marker_pages.jsonl"
  ["Stage 2 (sections)"]="data/extracted/joyful_science_marker_sections.json"
  ["Stage 2 (annotated)"]="data/extracted/joyful_science_marker_pages_annotated.jsonl"
  ["Stage 3 (chunks)"]="data/chunks/joyful_science_chunks_raw.jsonl"
  ["Stage 4 (mapped)"]="data/chunks/joyful_science_chunks_mapped.jsonl"
  ["English anchors"]="data/anchors/joyful_science_english_units.jsonl"
)

for label in "${!FILES[@]}"; do
  path="${FILES[$label]}"
  if [ -f "$path" ]; then
    if [[ "$path" == *.jsonl ]]; then
      lines=$(wc -l < "$path" 2>/dev/null)
      echo "  ✅ $label: $lines lines ($path)"
    else
      size=$(du -h "$path" | cut -f1)
      echo "  ✅ $label: $size ($path)"
    fi
    PASS=$((PASS + 1))
  else
    echo "  ⚠️  $label MISSING ($path)"
  fi
done
echo ""

# === Summary ===
echo "=========================================="
echo "  Result: $PASS passed, $FAIL failed"
echo "=========================================="

if [ "$FAIL" -gt 0 ]; then
  echo ""
  echo "Failed checks suggest one of:"
  echo "  - venv not activated → source .venv/bin/activate"
  echo "  - dependencies missing → poetry install"
  echo "  - HF models not cached → bash scripts/setup/05_warm_cache.sh"
  echo "  - LLM models not cached → bash scripts/setup/08_warm_llm.sh"
  echo "  - shell init not applied → bash scripts/setup/06_shell_init.sh && source ~/.bashrc"
  exit 1
fi
