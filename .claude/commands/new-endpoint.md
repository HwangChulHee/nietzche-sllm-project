`$ARGUMENTS`에 해당하는 새 FastAPI 엔드포인트를 Layered Architecture에 맞게 생성하라.

## 순서 (반드시 이 순서로)

1. **Schema** — `apps/backend/schemas/` 에 Pydantic 요청(Request) / 응답(Response) 모델 추가
2. **Service** — `apps/backend/services/` 에 비즈니스 로직 함수 추가 (DB/외부API 연동)
3. **Endpoint** — `apps/backend/api/v1/endpoints/` 에 라우터 함수 추가 (Schema만 알고, Service 호출)
4. **Router 등록** — `apps/backend/api/v1/api.py` 에 새 라우터 include

## 규칙
- 엔드포인트 함수는 비즈니스 로직을 직접 포함하지 않음
- 모든 함수는 async def
- SSE 응답은 StreamingResponse + `text/event-stream` 미디어 타입 사용
