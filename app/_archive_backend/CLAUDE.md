# Backend — 비주얼 노벨 sLLM 라우팅 가이드

> FastAPI + 비동기 PostgreSQL + SSE. 작품 결을 *얇은 sLLM 호출 라우터*로 흘려보냄.

---

## 레이어 책임

| 레이어 | 역할 |
|---|---|
| `api/v1/endpoints/` | HTTP 요청/응답 + SSE 스트림. 비즈니스 로직 금지 |
| `schemas/vn.py` | Pydantic 입출력 모델 (8개 엔드포인트 미러) |
| `services/llm_client.py` | 저수준 LLM 스트리밍 추상화 (Mock/VLLM) |
| `services/sllm_clients.py` | Persona / Explain / Summary 3종 ABC + 싱글턴 팩토리 |
| `services/mock_data.py` | 화면별 Mock 응답 풀 |
| `models/save.py` | SaveSlot SQLAlchemy 모델 (단일 슬롯, id=1 고정) |
| `db/session.py` | 비동기 PostgreSQL 세션 |
| `prompts/` | 시스템 프롬프트 3개 (persona / explain / summary) |
| `alembic/` | DB 마이그레이션 (002에 `save_slots` 신설) |

---

## sLLM 클라이언트 구조

`services/sllm_clients.py`에 ABC + 두 구현체:

```
PersonaClient(ABC)        # 차라투스트라 발화
├─ MockPersonaClient      # mock_data.PERSONA_*에서 yield
└─ VLLMPersonaClient      # 시스템 프롬프트 + LLMClient 호출

ExplainClient(ABC)        # 해설 동적 풀이
├─ MockExplainClient
└─ VLLMExplainClient

SummaryClient(ABC)        # 카운드오버/세이브 요약
├─ MockSummaryClient
└─ VLLMSummaryClient
```

싱글턴 팩토리: `get_persona_client()`, `get_explain_client()`, `get_summary_client()` — 환경변수 `LLM_MODE`로 분기.

`services/llm_client.py`는 더 *저수준* — vLLM OpenAI 호환 API SSE 스트리밍을 한 줄로 yield. VLLM* 클라이언트가 내부에서 사용.

---

## 8개 엔드포인트 (`/api/v1/`)

| 메서드 | 경로 | sLLM | 용도 |
|---|---|---|---|
| POST | `/respond` | Persona | 학습자 발화/[침묵] 응답 |
| POST | `/respond/auto` | Persona | 화면 진입 자동 발화 |
| POST | `/respond/farewell` | Persona | [작별을 고한다] 마지막 발화 |
| POST | `/explain` | Explain | [해설] [더 깊이 묻기] 동적 풀이 |
| POST | `/summarize` | Summary | 에피소드 간 카운드오버 요약 |
| GET | `/save` | — | 단일 슬롯 조회 |
| POST | `/save` | Summary (내부) | 저장 — Summary 동기 consume 후 upsert |
| DELETE | `/save` | — | 슬롯 삭제 |

응답 SSE 이벤트: `metadata` / `delta` / `done` / `error`.

---

## 환경변수

| 변수 | 기본값 | 용도 |
|---|---|---|
| `LLM_MODE` | `mock` | `mock` / `vllm` 토글 |
| `VLLM_BASE_URL` | `http://localhost:8002/v1` | vLLM OpenAI 호환 엔드포인트 |
| `VLLM_MODEL` | `nietzsche-epoch1` | 서빙 모델 이름 |
| `VLLM_API_KEY` | `dummy` | vLLM 인증 (사용 안 함, placeholder) |
| `PERSONA_PROMPT_FILE` | `prompts/persona_v1.txt` | 페르소나 시스템 프롬프트 |
| `EXPLAIN_PROMPT_FILE` | `prompts/explain_v1.txt` | 해설 시스템 프롬프트 |
| `SUMMARY_PROMPT_FILE` | `prompts/summary_v1.txt` | 요약 시스템 프롬프트 |
| `DATABASE_URL` | `postgresql+asyncpg://...` | DB 연결 |
| `CORS_ORIGINS` | `http://localhost:3000` | CORS 허용 origin |

`.env.example` 참조.

---

## DB 셋업

```bash
# 최초 1회 또는 nietzsche.db 없을 때
PYTHONPATH=. poetry run alembic upgrade head
```

`save_slots` 테이블 생성 (단일 슬롯, id=1 고정). 옛 `conversations`/`messages`는 Phase 2에서 drop됨.

---

## 모드 토글 패턴

```python
# 환경변수만 바꾸면 됨, 코드 수정 X
LLM_MODE=mock    # 시연 안정성
LLM_MODE=vllm    # 실제 추론 (Phase 9)
```

`get_*_client()` 팩토리가 `settings.LLM_MODE`를 보고 분기. Mock 응답 풀은 `services/mock_data.py`의 `PERSONA_*` / `EXPLAIN_*` / `SUMMARY_*` 상수.

---

## 의존성 추가

```bash
poetry add <패키지명>   # pyproject.toml 자동 업데이트
```

신규 LLM SDK / LangChain / LlamaIndex 도입 금지 (`docs/vn/VN_AGENTS.md` §3.5).
