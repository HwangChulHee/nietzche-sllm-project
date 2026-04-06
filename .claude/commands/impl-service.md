`apps/backend/services/$ARGUMENTS` 파일을 구현하라. 현재 빈 파일이므로 전체 구현이 필요하다.

## 각 파일의 구현 범위

### llm_service.py
- `core/config.py` 의 환경변수(RUNPOD_API_KEY, RUNPOD_ENDPOINT_ID)를 읽어 vLLM RunPod API 호출
- 니체 페르소나 시스템 프롬프트 정의 (1880년대 독일 철학자 말투, 어록 인용)
- `async def stream_nietzsche_response(user_message: str, context: list[str])` — SSE용 비동기 제너레이터
- RAG 컨텍스트(니체 어록)를 프롬프트에 삽입하는 로직 포함

### vector_service.py
- `core/config.py` 의 환경변수(QDRANT_URL, QDRANT_API_KEY)로 Qdrant 클라이언트 초기화
- `async def search_nietzsche_quotes(query: str, top_k: int = 5) -> list[str]` — 유사도 검색
- 텍스트 임베딩은 sentence-transformers 또는 OpenAI 임베딩 모델 사용

## 주의
- `core/config.py` 가 비어 있다면 먼저 pydantic-settings 기반으로 구현할 것
- 외부 서비스가 없어도 동작하도록 fallback/mock 분기 추가
