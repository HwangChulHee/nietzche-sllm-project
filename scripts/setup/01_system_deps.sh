#!/bin/bash
# ============================================================
# 시스템 의존성 설치 (apt 패키지)
# ============================================================
# 설치 항목:
#   - build-essential: 컴파일 도구
#   - git, curl, wget: 기본 CLI
#   - tesseract-ocr + tesseract-ocr-kor: OCR (백업용)
#   - ghostscript: PDF 처리
#   - poppler-utils: PDF 유틸
#   - libreoffice: 문서 변환 (marker가 필요)
#   - fonts-noto-cjk: 한중일 폰트 (PDF 렌더링)
# ============================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "apt 패키지 업데이트..."
apt-get update -qq

echo ""
echo "기본 개발 도구 설치..."
apt-get install -y -qq \
    build-essential \
    git \
    curl \
    wget \
    vim \
    htop \
    tree \
    unzip \
    ca-certificates

echo ""
echo "OCR 도구 설치 (Tesseract + 한국어)..."
apt-get install -y -qq \
    tesseract-ocr \
    tesseract-ocr-kor \
    tesseract-ocr-eng

echo ""
echo "PDF 처리 도구 설치..."
apt-get install -y -qq \
    ghostscript \
    poppler-utils \
    pdftk-java || echo -e "${YELLOW}  pdftk-java 스킵 (선택사항)${NC}"

echo ""
echo "Marker용 문서 변환 도구 설치..."
apt-get install -y -qq \
    libreoffice \
    libreoffice-common || echo -e "${YELLOW}  libreoffice 일부 스킵${NC}"

echo ""
echo "한중일 폰트 설치..."
apt-get install -y -qq \
    fonts-noto-cjk \
    fonts-noto-cjk-extra || echo -e "${YELLOW}  noto-cjk 일부 스킵${NC}"

echo ""
echo -e "${GREEN}✓ 시스템 의존성 설치 완료${NC}"
echo ""
echo "확인:"
echo -n "  tesseract: "; tesseract --version 2>&1 | head -1
echo -n "  git: "; git --version
echo -n "  ghostscript: "; gs --version
