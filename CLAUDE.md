# Nietzsche AI — 프로젝트 가이드

## 프로젝트 개요
니체 페르소나 기반 sLLM 철학 상담 서비스.
RAG(Qdrant) + QLoRA 파인튜닝(Gemma3/Llama3) + FastAPI + Next.js 구조.

## 앱 구조
- `apps/backend/` — FastAPI 백엔드 (Python 3.12, Poetry)
- `apps/frontend/` — Next.js 16 프론트엔드 (React 19, TypeScript)
- `scripts/` — 데이터 전처리 및 모델 학습 스크립트
- `data/raw/` — 니체 저서 원문, `data/processed/` — 임베딩용 JSONL

## 실행 명령어
```bash
# 백엔드
cd apps/backend && poetry run uvicorn main:app --reload   # :8000

# 프론트엔드
cd apps/frontend && npm run dev                            # :3000
```

## 핵심 설계 원칙
- 백엔드: Layered Architecture (Router → Schema → Service → Model)
- 모든 I/O는 async/await
- API 응답은 반드시 Pydantic Schema를 통해 타입 검증
- SSE(Server-Sent Events)로 스트리밍 응답

## 현재 구현 상태
- 구현 완료: main.py, 라우터, Layered Architecture 전체, 모든 models/schemas/services, DB(PostgreSQL+Qdrant), 37개 테스트 통과, UI 스켈레톤
- 미구현: Redux + SSE 클라이언트, 채팅 히스토리 API, JWT 인증, 데이터 파이프라인, Alembic 마이그레이션, QLoRA 파인튜닝, 배포

> 상세 구현 상태: `.context/current_status.md` 참조
