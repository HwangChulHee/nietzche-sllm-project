#!/bin/bash
# ============================================================
# Python 3.12 + Poetry + 가상환경 설정
# ============================================================
# 설치 항목:
#   - Python 3.12 (있으면 스킵)
#   - Poetry (공식 installer 사용)
#   - 프로젝트 가상환경 (ml/.venv/)
#   - Poetry 프로젝트 의존성
# ============================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ML_DIR="$PROJECT_ROOT/ml"

# Python 3.12 확인
echo "Python 3.12 확인..."
if command -v python3.12 &> /dev/null; then
    PYTHON_VERSION=$(python3.12 --version)
    echo -e "${GREEN}✓ $PYTHON_VERSION 이미 설치됨${NC}"
else
    echo -e "${YELLOW}Python 3.12 설치 시도...${NC}"
    # Ubuntu 22.04 기본은 3.10이라 deadsnakes PPA 필요할 수 있음
    if command -v add-apt-repository &> /dev/null; then
        add-apt-repository -y ppa:deadsnakes/ppa
        apt-get update -qq
        apt-get install -y python3.12 python3.12-venv python3.12-dev
    else
        echo -e "${YELLOW}⚠ Python 3.12 자동 설치 실패. 수동 설치 필요.${NC}"
        echo "RunPod 컨테이너에 이미 Python 3.12가 있을 수 있습니다."
        which python3 && python3 --version
    fi
fi

# Poetry 확인 및 설치
echo ""
echo "Poetry 확인..."
if command -v poetry &> /dev/null; then
    POETRY_VERSION=$(poetry --version)
    echo -e "${GREEN}✓ $POETRY_VERSION 이미 설치됨${NC}"
else
    echo "Poetry 설치 중..."
    curl -sSL https://install.python-poetry.org | python3 -

    # PATH에 Poetry 추가
    export PATH="$HOME/.local/bin:$PATH"

    # bashrc에 영구 추가
    if ! grep -q 'HOME/.local/bin' ~/.bashrc 2>/dev/null; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
    fi

    echo -e "${GREEN}✓ Poetry 설치 완료${NC}"
    poetry --version
fi

# Poetry 설정: 가상환경을 프로젝트 안에 생성
echo ""
echo "Poetry 설정..."
poetry config virtualenvs.in-project true
poetry config virtualenvs.prefer-active-python true

# 프로젝트 의존성 설치
echo ""
echo -e "${CYAN}프로젝트 의존성 설치 (ml/.venv/)...${NC}"
cd "$ML_DIR"

if [ ! -f "pyproject.toml" ]; then
    echo -e "${YELLOW}⚠ pyproject.toml 없음. 스킵.${NC}"
else
    poetry install --no-root
    echo -e "${GREEN}✓ Poetry 의존성 설치 완료${NC}"
fi

# 가상환경 확인
echo ""
if [ -d "$ML_DIR/.venv" ]; then
    VENV_PYTHON=$("$ML_DIR/.venv/bin/python" --version)
    echo -e "${GREEN}✓ 가상환경: $ML_DIR/.venv${NC}"
    echo -e "  Python: $VENV_PYTHON"
else
    echo -e "${YELLOW}⚠ 가상환경 미생성${NC}"
fi

echo ""
echo -e "${GREEN}✓ Python + Poetry 셋업 완료${NC}"
