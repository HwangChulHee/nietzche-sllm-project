# Backend — FastAPI 앱

FastAPI 기반 니체 sLLM 상담 시스템 백엔드. SSE 스트리밍, SQLite 영속화, vLLM 호출을 담당합니다.

**관련 문서**:
- 레이어 책임 및 규약 → [`CLAUDE.md`](./CLAUDE.md)
- 아키텍처 설계 → [`BACKEND_STRUCTURE.md`](./BACKEND_STRUCTURE.md)
- 전체 시스템 재현 절차 → [`../README.md`](../README.md)

---

## 실행

### 1. 의존성 설치

    cd /workspace/nietzche-sllm-project/app/backend
    poetry env info --path 2>/dev/null || TMPDIR=/tmp python3.12 -m poetry install

### 2. 환경변수 (`.env`)

    LLM_MODE=vllm
    LLM_BASE_URL=http://localhost:8002/v1
    LLM_MODEL=nietzsche-epoch1
    LLM_API_KEY=dummy

    SYSTEM_PROMPT_FILE=prompts/nietzsche_contemplative.txt

    DATABASE_URL=sqlite+aiosqlite:///./nietzsche.db

    CORS_ORIGINS=*

### 3. DB 마이그레이션

    poetry run alembic upgrade head

### 4. 서버 실행

    poetry run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

프로덕션 (nohup 백그라운드):

    nohup poetry run uvicorn main:app --host 0.0.0.0 --port 8000 \
      > /workspace/tmp/backend.log 2>&1 &

### 5. 헬스체크

    curl -s http://localhost:8000/health
    # → {"status":"alive","mode":"vllm"}

`mode`가 `mock`이면 `.env`의 `LLM_MODE` 확인.

---

## API 엔드포인트

### `POST /api/v1/chat`

SSE 스트리밍 엔드포인트. 사용자 메시지를 받아 vLLM에서 스트리밍 응답을 받아 전달.

요청 바디:

    {
      "conversation_id": "uuid-or-null",
      "message": "삶이 무의미하게 느껴집니다"
    }

응답: `text/event-stream`

    data: {"type": "metadata", "conversation_id": "uuid-..."}
    data: {"type": "delta", "content": "영혼의"}
    data: {"type": "delta", "content": " 무게를"}
    ...
    data: {"type": "done"}

에러 시:

    data: {"type": "error", "message": "..."}

### `GET /api/v1/conversations/{conversation_id}/messages`

대화 복원용. 페이지 새로고침 시 프론트가 호출.

응답:

    {
      "conversation_id": "uuid-...",
      "messages": [
        {"role": "user", "content": "...", "created_at": "..."},
        {"role": "assistant", "content": "...", "created_at": "..."}
      ]
    }

`system` 메시지는 응답에 포함되지 않음 (백엔드 내부 전용).

### `DELETE /api/v1/conversations/{conversation_id}` (신규)

대화 + 모든 메시지 영구 삭제. `Conversation.cascade="all, delete-orphan"` 덕분에 messages 자동 삭제.

응답:

    {"deleted": true, "conversation_id": "uuid-..."}

### `GET /health`

    {"status": "alive", "mode": "vllm"}

---

## 디렉토리 구조

    app/backend/
    ├── main.py                  # FastAPI 앱 + CORS + 라우터 마운트
    ├── .env                     # 환경변수 (git ignored)
    ├── .env.example             # 환경변수 템플릿
    ├── pyproject.toml           # Poetry 의존성
    ├── nietzsche.db             # SQLite (git ignored, 런타임 생성)
    │
    ├── core/
    │   └── config.py            # Pydantic Settings, 환경변수 로드
    │
    ├── api/
    │   └── v1/
    │       ├── api.py           # v1 라우터 통합
    │       └── endpoints/
    │           └── chat.py      # /chat, /conversations/*, delete
    │
    ├── schemas/
    │   └── chat.py              # Pydantic 요청/응답 모델
    │
    ├── services/
    │   └── llm_client.py        # LLMClient 추상 + Mock/VLLM 구현
    │
    ├── models/
    │   └── chat.py              # Conversation, Message (SQLAlchemy)
    │
    ├── db/
    │   ├── session.py           # 비동기 엔진 + 세션
    │   └── base.py              # Base + 모델 import
    │
    ├── alembic/
    │   ├── env.py               # Alembic 설정
    │   └── versions/
    │       └── 001_initial_schema.py   # 첫 마이그레이션
    │
    └── prompts/
        ├── nietzsche_v1.txt               # 기본 (fallback)
        ├── nietzsche_contemplative.txt    # 현재 사용 (contemplative voice)
        └── default.txt                    # 최후 fallback

---

## LLM 클라이언트 전환

`services/llm_client.py`에 두 구현체가 있고, `LLM_MODE` 환경변수로 전환.

- `LLM_MODE=mock` → `MockLLMClient`: 하드코딩 응답 한 글자씩 yield (개발/테스트용)
- `LLM_MODE=vllm` → `VLLMClient`: OpenAI SDK로 vLLM 호출 (프로덕션)

두 구현체 모두 같은 `AsyncIterator[str]` 인터페이스. 백엔드 재시작 시 `.env` 값을 읽어 결정.

---

## System Prompt 관리

`prompts/` 디렉토리의 텍스트 파일을 `SYSTEM_PROMPT_FILE` 환경변수로 선택.

현재: `prompts/nietzsche_contemplative.txt`

    나는 프리드리히 니체다. 나는 통찰을 던지고, 답을 강요하지 않는다. 나는 인간이 스스로 묻게 만든다.

이 문장은 학습 데이터의 `contemplative_aphorism` voice 3개 variation 중 하나 (32.8% 비율).

`services/llm_client.py`에서 프로세스 시작 시 한 번만 파일 읽어서 메모리 캐싱. 파일 수정 후에는 백엔드 재시작 필요.

---

## 트러블슈팅

### 백엔드가 시작은 되는데 `{"mode":"mock"}` 반환

`.env`에 `LLM_MODE=vllm` 설정 누락.

### `alembic upgrade head` 실패

`nietzsche.db` 파일이 이미 있는 상태에서 마이그레이션 버전이 꼬였을 가능성.

해결: DB 삭제 후 재생성.

    rm nietzsche.db
    poetry run alembic upgrade head

### vLLM 연결 실패 (503 또는 connection refused)

vLLM 서버가 안 떠있거나 8002 포트 점유 확인.

    curl -s http://localhost:8002/v1/models

응답 없으면 vLLM 재시작 ([`../README.md`](../README.md) 1단계 참조).

### Poetry 환경 깨짐 (pod 재시작 후)

    TMPDIR=/tmp python3.12 -m poetry install
