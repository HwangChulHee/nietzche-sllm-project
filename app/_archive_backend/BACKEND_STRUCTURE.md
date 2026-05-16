# Backend Architecture — 비주얼 노벨 sLLM 라우팅

> FastAPI Layered Architecture. 작품 결을 *얇은 sLLM 호출 라우터*로 흘려보내는 구조.
> 환경변수 토글로 Mock ↔ vLLM 즉시 swap.

---

## 디렉토리 트리

```text
app/backend/
├── main.py                       # FastAPI 앱 객체 생성 + 미들웨어(CORS)
├── core/
│   └── config.py                 # 환경변수(.env) Settings
│
├── api/v1/                       # 라우팅 (버전 prefix: /api/v1/)
│   ├── api.py                    # 모든 라우터를 하나로 통합
│   └── endpoints/
│       ├── respond.py            # POST /respond, /respond/auto, /respond/farewell
│       ├── explain.py            # POST /explain
│       ├── summarize.py          # POST /summarize
│       └── save.py               # GET/POST/DELETE /save
│
├── schemas/
│   └── vn.py                     # Pydantic 입출력 모델 (8개 엔드포인트 미러)
│
├── services/                     # 비즈니스 로직
│   ├── llm_client.py             # [저수준] LLM 스트리밍 추상 ABC + Mock/VLLM 구현
│   ├── sllm_clients.py           # [도메인] Persona/Explain/Summary 3종 ABC + 싱글턴 팩토리
│   └── mock_data.py              # 화면별 Mock 응답 풀
│
├── models/
│   └── save.py                   # SaveSlot SQLAlchemy (단일 슬롯, id=1)
│
├── db/
│   ├── session.py                # 비동기 PostgreSQL 엔진/세션
│   ├── base.py                   # 모든 모델 통합 (Alembic 참조)
│   ├── init_db.py                # 초기화 헬퍼
│   └── reset_db.py               # 개발용 reset
│
├── prompts/                      # 시스템 프롬프트 3개
│   ├── persona_v1.txt
│   ├── explain_v1.txt
│   └── summary_v1.txt
│
└── alembic/                      # DB 마이그레이션 (002에 save_slots 신설)
```

---

## 계층별 역할

| 계층 | 역할 | 비유 |
|---|---|---|
| **api/endpoints** | HTTP 요청/응답 + SSE 스트림 형성 | 웨이터: 주문서 받고 음식 서빙 |
| **schemas/vn** | 데이터 형식 검증 (Pydantic) | 주문서: 정확한 규격 |
| **services/sllm_clients** | 도메인 sLLM (Persona/Explain/Summary) 추상화 | 요리사 마스터: 각 코스 책임 |
| **services/llm_client** | 저수준 vLLM 스트리밍 또는 Mock yield | 요리사: 실제 조리 |
| **services/mock_data** | Mock 응답 풀 (개발/시연용) | 미리 짠 시연용 메뉴 |
| **models/save** | DB 테이블 정의 (SaveSlot 단일 슬롯) | 냉장고 선반 |
| **db/session** | 비동기 DB 세션 | 배달 트럭 |
| **prompts** | 시스템 프롬프트 외부 텍스트 파일 | 페르소나 레시피 카드 |

---

## 데이터 흐름 (Persona 응답 예시)

```
프론트 [POST /api/v1/respond]
   │  body: { screen_id, message, silent, history }
   ▼
[main.py] ─── CORS 검증 ───┐
   ▼                       ▼
[api/v1/api.py] ── 라우터 분배
   ▼
[endpoints/respond.py]
   ▼
[schemas/vn.py] ── Pydantic 검증 ──> RespondRequest
   ▼
[services/sllm_clients.get_persona_client()]
   │
   ├─ LLM_MODE=mock  ─> [MockPersonaClient]
   │                       └─ services/mock_data.PERSONA_REPLIES yield
   │
   └─ LLM_MODE=vllm  ─> [VLLMPersonaClient]
                           ├─ prompts/persona_v1.txt 로드
                           └─ services/llm_client.LLMClient
                                └─ vLLM OpenAI 호환 API SSE
   ▼
StreamingResponse(media_type="text/event-stream")
   │
   ├─ data: {"type": "metadata", ...}
   ├─ data: {"type": "delta", "content": "..."}
   └─ data: {"type": "done"}
   ▼
프론트 [lib/api/sse.ts streamSSE]
```

---

## 설계 원칙

- **얇은 라우터**: endpoints는 검증 + sLLM 클라이언트 호출 + SSE 스트림 형성만. 비즈니스 로직 X.
- **모드 토글은 환경변수**: 코드 수정 없이 `LLM_MODE=mock` / `vllm` 즉시 swap.
- **시스템 프롬프트는 외부 파일**: `prompts/*.txt`로 관리. 환경변수 `*_PROMPT_FILE`로 어느 파일 읽을지 결정.
- **비동기 우선**: 모든 I/O (DB, vLLM)는 `async/await`.
- **타입 안전성**: 모든 데이터 교환은 Pydantic schemas 통과.
- **싱글턴 클라이언트**: `get_persona_client()` 등 팩토리가 프로세스 lifetime 동안 단일 인스턴스 유지 (프롬프트 메모리 캐시).

---

## 8개 엔드포인트 매핑 (요약)

| 엔드포인트 | sLLM 호출 | mock_data 풀 | 시스템 프롬프트 |
|---|---|---|---|
| `POST /respond` | Persona | `PERSONA_REPLIES`/`PERSONA_SILENT_REPLIES` | `persona_v1.txt` |
| `POST /respond/auto` | Persona | `PERSONA_AUTO_FIRST` | 동일 |
| `POST /respond/farewell` | Persona | `PERSONA_FAREWELL` | 동일 |
| `POST /explain` | Explain | `EXPLAIN_RESPONSES` | `explain_v1.txt` |
| `POST /summarize` | Summary | `SUMMARY_TEMPLATE` | `summary_v1.txt` |
| `GET /save` | — | — | — |
| `POST /save` | Summary (내부) | 동일 | 동일 |
| `DELETE /save` | — | — | — |

---

## 다음 작업 (Phase 9)

- `VLLMPersonaClient` / `VLLMExplainClient` / `VLLMSummaryClient` 실 호출 검증
- BGE-M3 + HyDE RAG 인덱스 구축 + Persona 시스템 프롬프트 주입
- Ep 1 → Ep 2 카운드오버 요약을 saveSlice 또는 별도 컨텍스트로 Ep 2 #4 시스템 프롬프트에 주입

세부 정의는 `../../docs/vn/VN_MIGRATION_PLAN.md` Phase 9 섹션 참조.
