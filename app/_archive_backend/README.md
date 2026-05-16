# Backend — 비주얼 노벨 sLLM 라우팅

> ⚠️ **ARCHIVE**: 이 디렉토리는 폐기 노선. 2026-05-16 통합으로 활성 백엔드는 `../ml-backend/` (Node + Express + llama.cpp + sqlite-vec). 본 문서는 옛 FastAPI 구현의 회고용 보존 자료.

FastAPI 기반 *얇은 sLLM 호출 라우터*. 8개 엔드포인트가 SSE 스트림으로 차라투스트라 발화 / 해설 동적 풀이 / 요약을 흘려보낸다.

**관련 문서**:
- 레이어 책임 / sLLM 클라이언트 / 환경변수 → [`CLAUDE.md`](./CLAUDE.md)
- 아키텍처 도해 → [`BACKEND_STRUCTURE.md`](./BACKEND_STRUCTURE.md)
- 시연 셋업 → [`../README.md`](../README.md)
- 작품 정책 → [`../../docs/vn/VN_AGENTS.md`](../../docs/vn/VN_AGENTS.md)

---

## 실행

### 1. 의존성 설치 (최초 1회)

```bash
cd app/backend
poetry env info --path 2>/dev/null || TMPDIR=/tmp python3.12 -m poetry install
```

### 2. 환경변수 (`.env`)

`.env.example` 복사 후 수정:

```bash
# Mock 모드 (시연 권장)
LLM_MODE=mock

# vLLM 모드 (Phase 9, RunPod 환경)
LLM_MODE=vllm
VLLM_BASE_URL=http://localhost:8002/v1
VLLM_MODEL=nietzsche-epoch1
VLLM_API_KEY=dummy

# 시스템 프롬프트 (3종)
PERSONA_PROMPT_FILE=prompts/persona_v1.txt
EXPLAIN_PROMPT_FILE=prompts/explain_v1.txt
SUMMARY_PROMPT_FILE=prompts/summary_v1.txt

# DB
DATABASE_URL=postgresql+asyncpg://nietzsche:nietzsche@localhost:5432/nietzsche

# CORS
CORS_ORIGINS=http://localhost:3000
```

### 3. DB 마이그레이션 (최초 1회)

```bash
PYTHONPATH=. poetry run alembic upgrade head
```

`save_slots` 테이블 생성. 옛 `conversations`/`messages`는 Phase 2에서 drop됨.

### 4. 서버 실행

```bash
PYTHONPATH=. poetry run uvicorn main:app --port 8000

# 또는 hot reload
PYTHONPATH=. poetry run uvicorn main:app --port 8000 --reload
```

### 5. 헬스체크

```bash
curl -s http://localhost:8000/health
# → {"status":"alive","mode":"mock"}    (또는 "vllm")
```

`mode`가 예상과 다르면 `.env`의 `LLM_MODE` 확인.

---

## API 엔드포인트

모두 prefix `/api/v1/`. SSE 응답은 `text/event-stream`.

### POST `/respond` — 학습자 발화 응답

Persona sLLM. 학습자 자유 발화 또는 [침묵] 응답.

```json
{
  "screen_id": "ep1_screen5_meeting",
  "message": "산에서 내려오는 길에...",
  "silent": false,
  "history": [{"role": "assistant", "content": "그대. 어디서 왔는가."}]
}
```

`silent: true`면 시스템 프롬프트에 침묵 지시 주입.

### POST `/respond/auto` — 화면 진입 자동 발화

```json
{ "screen_id": "ep1_screen6_walking", "history": [...] }
```

#6/#7 동행/시장 원경 진입 시 차라투스트라 첫 발화 자동 생성.

### POST `/respond/farewell` — [작별을 고한다] 발화

```json
{ "screen_id": "ep1_screen7_market_distant", "history": [...] }
```

### POST `/explain` — [더 깊이 묻기] 동적 풀이

Explain sLLM. 정적 풀이 위에 학습자 follow-up 질문에 응답.

```json
{
  "screen_id": "ep1_screen2_summit",
  "query": "왜 산이었는가",
  "history": [...]
}
```

### POST `/summarize` — 카운드오버 요약

Summary sLLM. Ep 1 → Ep 2 transition 시 백그라운드 호출.

### GET `/save` / POST `/save` / DELETE `/save`

단일 슬롯 (id=1 고정). POST는 내부에서 Summary sLLM 동기 호출 후 upsert.

---

## SSE 응답 이벤트

| type | 페이로드 |
|---|---|
| `metadata` | `{"screen_id": "...", "kind": "..."}` 등 |
| `delta` | `{"content": "..."}` 토큰 단위 |
| `done` | `{}` 스트림 종료 |
| `error` | `{"message": "..."}` |

```
data: {"type": "metadata", "screen_id": "ep1_screen5_meeting", "silent": false}

data: {"type": "delta", "content": "흥"}

data: {"type": "delta", "content": "미"}

data: {"type": "done"}
```

---

## 디렉토리 구조

```
app/backend/
├── main.py                       # FastAPI 앱 + CORS
├── core/config.py                # Settings (.env 로드)
├── api/v1/
│   ├── api.py                    # 라우터 등록
│   └── endpoints/
│       ├── respond.py            # POST /respond, /respond/auto, /respond/farewell
│       ├── explain.py            # POST /explain
│       ├── summarize.py          # POST /summarize
│       └── save.py               # GET/POST/DELETE /save
├── services/
│   ├── llm_client.py             # 저수준 LLM 스트리밍 추상 (Mock/VLLM)
│   ├── sllm_clients.py           # Persona/Explain/Summary 3종 ABC
│   └── mock_data.py              # 화면별 Mock 응답 풀
├── schemas/vn.py                 # Pydantic 모델 (8개 엔드포인트)
├── models/save.py                # SaveSlot SQLAlchemy
├── db/
│   ├── session.py                # 비동기 PostgreSQL 세션
│   ├── base.py                   # 모든 모델 통합
│   └── reset_db.py               # 개발용 reset 헬퍼
├── prompts/
│   ├── persona_v1.txt
│   ├── explain_v1.txt
│   └── summary_v1.txt
└── alembic/                      # 002 마이그레이션 (save_slots)
```

---

## Mock vs vLLM 토글

```bash
# 시연 안정성 (기본)
LLM_MODE=mock

# 실제 추론 (Phase 9)
LLM_MODE=vllm
```

`services/sllm_clients.py`의 싱글턴 팩토리(`get_persona_client()` 등)가 `settings.LLM_MODE`로 분기. `Mock*Client`는 `mock_data.py`의 응답 풀에서 yield, `VLLM*Client`는 `LLMClient` 저수준으로 vLLM OpenAI 호환 API 호출.

코드 수정 없이 환경변수만 토글.

---

## 트러블슈팅

### `/save` 가 500 응답
DB 마이그레이션 미적용. `poetry run alembic upgrade head` 실행.

### `/health`가 `{"mode":"mock"}` 반환되는데 vLLM 쓰고 싶음
`.env`의 `LLM_MODE=vllm` 확인 후 백엔드 재시작.

### CORS 에러
`.env`의 `CORS_ORIGINS`에 프론트엔드 origin 추가 (`http://localhost:3000`). 여러 origin은 `,` 구분.

### vLLM 연결 실패
1. vLLM 서버 살아있는지: `curl http://localhost:8002/v1/models`
2. `VLLM_BASE_URL`이 정확한지 (RunPod 환경이면 Cloudflare tunnel URL)
3. 백엔드 로그에서 에러 확인
