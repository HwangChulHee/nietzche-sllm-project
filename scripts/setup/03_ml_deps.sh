#!/bin/bash
# ============================================================
# ML 의존성 설치
# ============================================================
# 설치 항목:
#   - marker-pdf: PDF OCR + 구조화 (Poetry로 설치, 정식 의존성)
#   - huggingface-hub: 모델 다운로드 (Poetry로 설치)
#   - vllm: LLM 추론 서버 (pip으로 설치, RunPod PyTorch 보존)
#
# 환경변수:
#   SKIP_VLLM=true 이면 vLLM 스킵
#
# 주의:
#   - RunPod의 PyTorch 이미지 사용을 가정함
#   - vLLM 설치 시 기존 PyTorch를 보존하기 위해 --no-deps 사용 후
#     누락된 의존성만 별도 설치
# ============================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ML_DIR="$PROJECT_ROOT/ml"

cd "$ML_DIR"

# 가상환경 확인
if [ ! -d ".venv" ]; then
    echo -e "${RED}✗ .venv 없음. 먼저 02_python_poetry.sh 실행${NC}"
    exit 1
fi

VENV_PIP="$ML_DIR/.venv/bin/pip"
VENV_PYTHON="$ML_DIR/.venv/bin/python"

if [ ! -x "$VENV_PIP" ]; then
    echo -e "${RED}✗ $VENV_PIP 없음${NC}"
    exit 1
fi

echo -e "${CYAN}사용 중인 Python: $($VENV_PYTHON --version)${NC}"
echo -e "${CYAN}사용 중인 pip:    $VENV_PIP${NC}"

# Poetry 명령 (PATH 보장)
export PATH="$HOME/.local/bin:$PATH"

# 현재 PyTorch 버전 기록 (vLLM 설치 후 비교용)
echo ""
echo "기존 PyTorch 확인..."
TORCH_VERSION=$($VENV_PYTHON -c "import torch; print(torch.__version__)" 2>/dev/null || echo "none")
TORCH_CUDA=$($VENV_PYTHON -c "import torch; print(torch.version.cuda)" 2>/dev/null || echo "none")
if [ "$TORCH_VERSION" != "none" ]; then
    echo -e "${GREEN}✓ PyTorch $TORCH_VERSION (CUDA $TORCH_CUDA) 이미 설치됨${NC}"
else
    echo -e "${YELLOW}  PyTorch 미설치 (RunPod PyTorch 이미지 아님?)${NC}"
fi

# ━━━ Marker 설치 (Poetry) ━━━
echo ""
echo -e "${CYAN}━━━ Marker 설치 (Poetry) ━━━${NC}"
echo -e "${YELLOW}  ※ Poetry resolution에 시간 걸릴 수 있음 (3-10분)${NC}"

if $VENV_PYTHON -c "import marker" 2>/dev/null; then
    MARKER_VER=$($VENV_PYTHON -c "import marker; print(getattr(marker, '__version__', 'unknown'))")
    echo -e "${GREEN}✓ marker-pdf 이미 설치됨: $MARKER_VER${NC}"
else
    cd "$ML_DIR"
    poetry add marker-pdf
    echo -e "${GREEN}✓ marker-pdf 설치 완료 (pyproject.toml에 추가됨)${NC}"
fi

# ━━━ Hugging Face Hub (Poetry) ━━━
echo ""
echo -e "${CYAN}━━━ Hugging Face Hub 설치 (Poetry) ━━━${NC}"

if $VENV_PYTHON -c "import huggingface_hub" 2>/dev/null; then
    HF_VER=$($VENV_PYTHON -c "import huggingface_hub; print(huggingface_hub.__version__)")
    echo -e "${GREEN}✓ huggingface-hub 이미 설치됨: $HF_VER${NC}"
else
    cd "$ML_DIR"
    poetry add huggingface-hub
    echo -e "${GREEN}✓ huggingface-hub 설치 완료${NC}"
fi

# ━━━ vLLM 설치 (pip, PyTorch 보존) ━━━
if [ "${SKIP_VLLM:-false}" = "true" ]; then
    echo ""
    echo -e "${YELLOW}vLLM 스킵됨 (SKIP_VLLM=true)${NC}"
    echo -e "${YELLOW}  나중에 설치하려면:${NC}"
    echo -e "${YELLOW}    bash scripts/setup/03_ml_deps.sh${NC}"
else
    echo ""
    echo -e "${CYAN}━━━ vLLM 설치 (pip, PyTorch 보존 모드) ━━━${NC}"

    # GPU 확인
    if ! command -v nvidia-smi &> /dev/null; then
        echo -e "${YELLOW}⚠ nvidia-smi 없음. GPU 미감지. vLLM 스킵.${NC}"
    else
        echo ""
        echo "GPU 정보:"
        nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
        echo ""

        if $VENV_PYTHON -c "import vllm" 2>/dev/null; then
            VLLM_VER=$($VENV_PYTHON -c "import vllm; print(vllm.__version__)")
            echo -e "${GREEN}✓ vLLM 이미 설치됨: $VLLM_VER${NC}"
        else
            echo -e "${YELLOW}vLLM 설치 중... (5-10분 소요)${NC}"
            echo -e "${YELLOW}※ RunPod PyTorch와 호환되도록 설치${NC}"

            # PyTorch 버전 확인 후 호환 vLLM 설치
            # vLLM은 PyTorch 의존성이 엄격해서 충돌 가능
            # --no-build-isolation 으로 기존 환경 사용
            $VENV_PIP install vllm --no-build-isolation || {
                echo -e "${RED}✗ vLLM 일반 설치 실패${NC}"
                echo -e "${YELLOW}대안 시도: 특정 버전 설치${NC}"
                $VENV_PIP install vllm==0.6.3 --no-build-isolation || {
                    echo -e "${RED}✗ vLLM 설치 실패. 수동 설치 필요.${NC}"
                    echo -e "${YELLOW}참고: https://docs.vllm.ai/en/latest/getting_started/installation.html${NC}"
                }
            }

            # PyTorch 버전 변경 확인
            echo ""
            NEW_TORCH=$($VENV_PYTHON -c "import torch; print(torch.__version__)" 2>/dev/null || echo "none")
            if [ "$NEW_TORCH" != "$TORCH_VERSION" ] && [ "$TORCH_VERSION" != "none" ]; then
                echo -e "${YELLOW}⚠ PyTorch 버전이 변경됨: $TORCH_VERSION → $NEW_TORCH${NC}"
                echo -e "${YELLOW}  RunPod의 PyTorch가 vLLM에 의해 교체되었을 수 있음${NC}"
            fi
        fi
    fi
fi

# 설치 확인
echo ""
echo -e "${CYAN}━━━ 설치된 패키지 확인 ━━━${NC}"
$VENV_PYTHON << 'PYEOF'
import importlib

packages = [
    ('torch', 'PyTorch'),
    ('marker', 'Marker'),
    ('huggingface_hub', 'HuggingFace Hub'),
    ('fitz', 'PyMuPDF'),
    ('pydantic', 'Pydantic'),
]

for pkg, label in packages:
    try:
        m = importlib.import_module(pkg)
        ver = getattr(m, '__version__', 'unknown')
        print(f'  ✓ {label}: {ver}')
    except ImportError:
        print(f'  ✗ {label}: 미설치')

# vLLM은 별도 (선택적)
try:
    import vllm
    print(f'  ✓ vLLM: {vllm.__version__}')
except ImportError:
    print(f'  - vLLM: 미설치 (스킵됨)')

# CUDA 확인
try:
    import torch
    if torch.cuda.is_available():
        print(f'\n  CUDA: {torch.version.cuda}')
        print(f'  GPU count: {torch.cuda.device_count()}')
        for i in range(torch.cuda.device_count()):
            print(f'  GPU {i}: {torch.cuda.get_device_name(i)}')
    else:
        print(f'\n  CUDA: 사용 불가')
except Exception as e:
    print(f'\n  CUDA 확인 실패: {e}')
PYEOF

echo ""
echo -e "${GREEN}✓ ML 의존성 설치 완료${NC}"
