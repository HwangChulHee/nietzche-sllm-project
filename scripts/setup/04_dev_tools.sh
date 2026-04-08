#!/bin/bash
# ============================================================
# 개발 도구 설치 (Claude Code, Git 설정)
# ============================================================
# 설치 항목:
#   - Claude Code CLI (npm으로 설치)
#   - Node.js 20 LTS (없으면)
#   - Git user 설정
# ============================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Git 설정 (프로젝트별이 아니라 글로벌)
GIT_USER_NAME="HwangChulHee"
GIT_USER_EMAIL="kum15479@naver.com"

echo "Git 설정..."
git config --global user.name "$GIT_USER_NAME"
git config --global user.email "$GIT_USER_EMAIL"
git config --global init.defaultBranch main
git config --global pull.rebase false
echo -e "${GREEN}✓ Git user: $GIT_USER_NAME <$GIT_USER_EMAIL>${NC}"

# Node.js 확인 (Claude Code가 npm 기반)
echo ""
echo "Node.js 확인..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}✓ Node.js $NODE_VERSION 이미 설치됨${NC}"
else
    echo -e "${YELLOW}Node.js 설치 중 (v20 LTS)...${NC}"
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
    echo -e "${GREEN}✓ Node.js $(node --version) 설치됨${NC}"
fi

# npm 확인
if ! command -v npm &> /dev/null; then
    echo -e "${YELLOW}⚠ npm 없음. Claude Code 스킵.${NC}"
    exit 0
fi

# Claude Code 설치
echo ""
echo "Claude Code 설치..."
if command -v claude &> /dev/null; then
    CLAUDE_VERSION=$(claude --version 2>/dev/null || echo "unknown")
    echo -e "${GREEN}✓ Claude Code 이미 설치됨: $CLAUDE_VERSION${NC}"
else
    # Claude Code 공식 설치 방법
    npm install -g @anthropic-ai/claude-code
    echo -e "${GREEN}✓ Claude Code 설치 완료${NC}"
fi

# 확인
echo ""
echo -e "${CYAN}━━━ 설치 확인 ━━━${NC}"
echo -n "  git user: "; git config --global user.name
echo -n "  git email: "; git config --global user.email
echo -n "  node: "; node --version 2>/dev/null || echo "미설치"
echo -n "  npm: "; npm --version 2>/dev/null || echo "미설치"
echo -n "  claude: "; claude --version 2>/dev/null || echo "미설치"

echo ""
echo -e "${GREEN}✓ 개발 도구 설치 완료${NC}"
echo ""
echo -e "${YELLOW}다음 단계:${NC}"
echo "  Claude Code 로그인: claude login"
