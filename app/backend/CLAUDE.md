# Backend — FastAPI 가이드

## 레이어 책임
- `api/v1/endpoints/` : HTTP 요청/응답만 처리, 비즈니스 로직 금지
- `schemas/` : Pydantic 입출력 모델
- `services/` : 외부 API(vLLM, Qdrant) 연동 및 핵심 로직
- `models/` : SQLAlchemy 테이블 정의
- `db/session.py` : 비동기 PostgreSQL 세션

## 주요 외부 서비스
- Qdrant: 니체 저서 벡터 검색 (RAG)
- vLLM on RunPod: 파인튜닝 모델 추론
- PostgreSQL: 대화 기록 저장

## 의존성 추가
```bash
poetry add <패키지명>   # pyproject.toml 자동 업데이트
```

## 테스트
```bash
poetry run pytest
```
