# Nietzsche Data Pipeline

니체 저서 북스캔 PDF를 정제하여 SFT 학습 데이터로 변환하는 파이프라인.

## 구조

- `data_pipeline/`: 파이프라인 코드 (extraction → segmentation → alignment → refinement → validation → output)
- `scripts/`: 스테이지별 실행 스크립트 (`01_extract.py` 등)
- `data/`: 입출력 데이터 (gitignore)
- `models/`: 모델 가중치 (gitignore)

## 실행 환경

- Python 3.12
- Poetry

## 설치

```bash
poetry install
```

## 파이프라인 스테이지

1. **Extraction**: PDF → 페이지별 텍스트 블록 (pymupdf)
2. **Segmentation**: 섹션(서문/본편/부록) 감지 + 아포리즘 분할
3. **Alignment**: 한국어 Raw ↔ 영어 Gutenberg Anchor 매핑
4. **Refinement**: LLM(Gemma 4 26B-A4B)으로 OCR 노이즈 제거 및 문체 복원
5. **Validation**: 자동 검증 + 핵심 아포리즘 수동 검증
6. **Output**: SFT 학습 데이터 JSONL 생성

## 개발 중

Phase 1: 즐거운 학문 MVP (~2026-04-13 중간발표)