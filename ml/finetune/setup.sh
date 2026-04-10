#!/usr/bin/env bash
# =============================================================================
# Nietzsche sLLM finetune environment setup
#
# Usage:
#   cd /workspace/nietzche-sllm-project/ml/finetune
#   bash setup.sh
#
# Assumes:
#   - RunPod pod with NVIDIA A100 (sm_80) or compatible
#   - /workspace is a persistent Volume
#   - Run from finetune/ directory
# =============================================================================

set -e  # 에러 발생 시 즉시 중단

FINETUNE_DIR="/workspace/nietzche-sllm-project/ml/finetune"
VENV_DIR="${FINETUNE_DIR}/.venv"

echo "============================================"
echo "[1/8] Workspace cache 환경변수 설정"
echo "============================================"
mkdir -p /workspace/.cache/pip /workspace/.cache/huggingface /workspace/tmp
export PIP_CACHE_DIR=/workspace/.cache/pip
export TMPDIR=/workspace/tmp
export HF_HOME=/workspace/.cache/huggingface

# .bashrc에 영구 저장 (이미 있으면 중복 안 함)
if ! grep -q "PIP_CACHE_DIR=/workspace" ~/.bashrc; then
    cat >> ~/.bashrc << 'EOF'
export PIP_CACHE_DIR=/workspace/.cache/pip
export TMPDIR=/workspace/tmp
export HF_HOME=/workspace/.cache/huggingface
export PATH="/root/.local/bin:$PATH"
EOF
fi

echo "============================================"
echo "[2/8] Python 3.12 설치 확인"
echo "============================================"
if ! command -v python3.12 &> /dev/null; then
    echo "Python 3.12 없음 → 설치 중..."
    apt update
    apt install -y python3.12 python3.12-venv python3.12-dev
fi
python3.12 --version

echo "============================================"
echo "[3/8] Poetry 설치 확인"
echo "============================================"
if ! command -v poetry &> /dev/null; then
    echo "Poetry 없음 → 설치 중..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="/root/.local/bin:$PATH"
fi
poetry --version

echo "============================================"
echo "[4/8] 기존 .venv 정리 (깨진 venv 제거)"
echo "============================================"
cd "${FINETUNE_DIR}"
if [ -d "${VENV_DIR}" ]; then
    # venv가 valid한지 확인
    if ! "${VENV_DIR}/bin/python" --version &> /dev/null; then
        echo ".venv가 깨져있음 → 삭제"
        rm -rf "${VENV_DIR}"
    else
        echo ".venv 정상"
    fi
fi

echo "============================================"
echo "[5/8] Poetry 환경 생성 + 기본 의존성"
echo "============================================"
poetry config virtualenvs.in-project true --local
poetry env use python3.12
poetry install || echo "(poetry install 일부 경고는 무시 가능)"

echo "============================================"
echo "[6/8] PyTorch + xformers (cu124)"
echo "============================================"
poetry run pip install torch==2.6.0 xformers==0.0.29.post3 \
    --index-url https://download.pytorch.org/whl/cu124

echo "============================================"
echo "[7/8] Unsloth 스택 (의존성 수동 처리)"
echo "============================================"
# unsloth가 의존성 선언이 부실해서 수동으로 다 깔아야 함

# 1단계: 기본 ML 스택
poetry run pip install \
    bitsandbytes \
    "triton==3.2.0" \
    huggingface_hub \
    transformers \
    datasets \
    peft \
    trl \
    accelerate \
    sentencepiece \
    protobuf \
    wandb \
    psutil \
    ninja \
    einops

# 2단계: torchvision (unsloth_zoo가 import함)
poetry run pip install torchvision --index-url https://download.pytorch.org/whl/cu124

# 3단계: unsloth + unsloth_zoo
# 주의: unsloth_zoo는 torchao>=0.13을 의존성으로 끌어옴
poetry run pip install \
    "unsloth @ git+https://github.com/unslothai/unsloth.git" \
    unsloth_zoo

# 4단계 (반드시 마지막): torchao 다운그레이드
# torchao 0.13+는 torch 2.7 API(torch.utils._pytree.register_constant)를 사용
# 우리는 torch 2.6을 쓰므로 충돌 → 0.12로 강제 다운그레이드
# unsloth_zoo의 dependency warning은 무시 가능 (실제로 0.12에서 동작)
poetry run pip install "torchao==0.12.0" --force-reinstall

echo "============================================"
echo "[8/8] 검증"
echo "============================================"
poetry run python -c "
import torch
from unsloth import FastLanguageModel
print('=' * 40)
print('torch:', torch.__version__)
print('cuda:', torch.cuda.is_available())
print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')
print('=' * 40)
print('SETUP COMPLETE')
"

echo ""
echo "============================================"
echo "Done. 다음 단계:"
echo "  1. poetry run wandb login"
echo "  2. poetry run python scripts/train.py"
echo "============================================"