#!/bin/bash
# ============================================================
# 니체 sLLM 프로젝트 - 전체 환경 설치 스크립트
# ============================================================
# 사용법:
#   bash scripts/setup/install_all.sh
#   bash scripts/setup/install_all.sh --skip-vllm    # GPU 없거나 나중에
#   bash scripts/setup/install_all.sh --skip-claude  # Claude Code 스킵
#
# 설치 단계:
#   1. 시스템 의존성 (apt)
#   2. Python 3.12 + Poetry + 가상환경
#   3. ML 의존성 (Marker, vLLM, HuggingFace CLI)
#   4. 개발 도구 (Claude Code, Git 설정)
# ============================================================

set -e

# 색상
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# 스크립트 위치
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 옵션 파싱
SKIP_VLLM=false
SKIP_CLAUDE=false
SKIP_SYSTEM=false

for arg in "$@"; do
    case $arg in
        --skip-vllm)   SKIP_VLLM=true; shift ;;
        --skip-claude) SKIP_CLAUDE=true; shift ;;
        --skip-system) SKIP_SYSTEM=true; shift ;;
        -h|--help)
            echo "사용법: $0 [옵션]"
            echo ""
            echo "옵션:"
            echo "  --skip-vllm     vLLM 설치 스킵"
            echo "  --skip-claude   Claude Code 설치 스킵"
            echo "  --skip-system   시스템 패키지 스킵 (apt 권한 없을 때)"
            exit 0
            ;;
    esac
done

echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  니체 sLLM 프로젝트 환경 설치                              ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Project root: ${GREEN}$PROJECT_ROOT${NC}"
echo -e "Skip vLLM:    ${YELLOW}$SKIP_VLLM${NC}"
echo -e "Skip Claude:  ${YELLOW}$SKIP_CLAUDE${NC}"
echo -e "Skip system:  ${YELLOW}$SKIP_SYSTEM${NC}"
echo ""

read -p "계속 진행하시겠습니까? [Y/n] " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]; then
    echo "설치 취소됨."
    exit 0
fi

# 1. 시스템 의존성
if [ "$SKIP_SYSTEM" = false ]; then
    echo ""
    echo -e "${CYAN}━━━ [1/4] 시스템 의존성 ━━━${NC}"
    bash "$SCRIPT_DIR/01_system_deps.sh"
else
    echo -e "${YELLOW}[1/4] 시스템 의존성 스킵${NC}"
fi

# 2. Python + Poetry
echo ""
echo -e "${CYAN}━━━ [2/4] Python + Poetry ━━━${NC}"
bash "$SCRIPT_DIR/02_python_poetry.sh"

# 3. ML 의존성
echo ""
echo -e "${CYAN}━━━ [3/4] ML 의존성 ━━━${NC}"
SKIP_VLLM=$SKIP_VLLM bash "$SCRIPT_DIR/03_ml_deps.sh"

# 4. 개발 도구
if [ "$SKIP_CLAUDE" = false ]; then
    echo ""
    echo -e "${CYAN}━━━ [4/4] 개발 도구 ━━━${NC}"
    bash "$SCRIPT_DIR/04_dev_tools.sh"
else
    echo -e "${YELLOW}[4/4] 개발 도구 스킵${NC}"
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✓ 설치 완료                                                ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "다음 단계:"
echo -e "  ${CYAN}cd $PROJECT_ROOT/ml${NC}"
echo -e "  ${CYAN}source .venv/bin/activate${NC}"
echo -e "  ${CYAN}python --version${NC}"
echo ""
