# Track 2 진행 상황 및 검증 가이드

## 완료 사항

### Step 1~2: 백엔드 기본 셋업 + DB 통합 ✅

- FastAPI 앱 (`main.py`) — CORS, 라우터, 헬스체크
- 환경변수 시스템 (`core/config.py`, `.env.example`, `.env`)
- LLM 클라이언트 추상화 (`services/llm_client.py`)
  - `MockLLMClient`: 니체풍 가짜 응답 5개, 한 글자씩 스트리밍
  - `VLLMClient`: OpenAI SDK 기반, vLLM 서버 호출
  - `LLM_MODE` 환경변수로 전환 (mock / vllm)
- 시스템 프롬프트 (`prompts/nietzsche_v1.txt`, `default.txt`)
- API 엔드포인트
  - `POST /api/v1/chat` — SSE 스트리밍 (metadata → delta → done)
  - `GET /api/v1/conversations/{id}/messages` — 대화 복원
- DB 모델 (`models/chat.py`) — Conversation, Message
- Alembic 마이그레이션 (`alembic/versions/001_initial_schema.py`)
- PostgreSQL 비동기 세션 (`db/session.py`)

### Step 3~5: 프론트엔드 + 채팅 UI + 디자인 ✅

- Next.js 16 App Router 라우팅
  - `/` — 새 대화 (빈 채팅창 + 니체 인용문)
  - `/chat/[conversationId]` — 기존 대화 로드 + 채팅
- Redux Toolkit 상태 관리 (`lib/store/chatSlice.ts`)
  - messages, isStreaming, messagesLoading, error 상태
  - fetchMessages 비동기 thunk (pending/fulfilled/rejected 처리)
- SSE 스트리밍 훅 (`lib/hooks/useStreamingChat.ts`)
  - fetch + ReadableStream으로 SSE 파싱
  - 첫 대화 시 `router.replace(/chat/${id})`로 URL 자동 업데이트
- 컴포넌트
  - `Header.tsx` — 공통 헤더 + "새 대화" 링크
  - `ChatInput.tsx` — Enter 전송, Shift+Enter 줄바꿈
  - `MessageBubble.tsx` — user(우측)/assistant(좌측), 스트리밍 커서
- 빈티지 디자인 적용 완료
  - 색상: 오프화이트 베이지 + 다크 브라운 + 와인 레드
  - 폰트: Georgia 세리프
  - 그라데이션/보라색/네온/둥근 모서리 없음

### Step 6: VLLMClient 구현 ✅

- `openai.AsyncOpenAI` 기반, `base_url`/`api_key`/`model` 설정으로 동작
- `.env`에서 `LLM_MODE=vllm`으로 바꾸면 즉시 전환

### 빌드 검증 ✅

- `next build` — TypeScript 에러 없이 성공
- `from main import app` — FastAPI 정상 로드 확인

---

## 로컬 검증 절차

### 사전 준비

- Docker Desktop 실행 중인지 확인
- Node.js 18+ 설치 확인 (`node -v`)
- Python 3.11+ 설치 확인 (`python3 -V`)
- Poetry 설치 확인 (`poetry --version`)

### 1단계: PostgreSQL 시작

```bash
cd nietzche-sllm-project
docker compose up -d db
```

정상 확인:
```bash
docker compose ps
# nietzsche-db   postgres:16   running   0.0.0.0:5432->5432/tcp
```

### 2단계: 백엔드 셋업 + 실행

```bash
cd app/backend

# .env 파일 확인 (이미 생성되어 있음, 없으면 복사)
# cp .env.example .env

# 의존성 설치
poetry install

# DB 마이그레이션
poetry run alembic upgrade head

# 서버 실행
poetry run uvicorn main:app --reload --port 8000
```

정상 확인:
```bash
curl http://localhost:8000/health
# {"status":"alive","mode":"mock"}
```

### 3단계: 프론트엔드 실행

새 터미널에서:
```bash
cd app/frontend
npm install
npm run dev
```

브라우저에서 `http://localhost:3000` 접속.

### 4단계: 시나리오 검증

| # | 시나리오 | 확인할 것 |
|---|---------|----------|
| 1 | `localhost:3000` 접속 | 빈 채팅창, "무엇이 그대를 심연으로 이끌었는가?" 인용문 표시 |
| 2 | 메시지 입력 + Enter | user 버블 즉시 표시 → mock 응답 한 글자씩 스트리밍 |
| 3 | 스트리밍 완료 후 | URL이 `/chat/{uuid}`로 자동 변경됨 |
| 4 | 같은 페이지에서 후속 메시지 전송 | 같은 대화에 메시지 추가, URL 유지 |
| 5 | 페이지 새로고침 (F5) | 메시지 히스토리가 DB에서 복원됨 |
| 6 | 헤더의 "새 대화" 클릭 | `/`로 이동, 빈 채팅창 |

### 5단계: 문제 발생 시

**백엔드가 안 뜰 때**
- `.env` 파일이 `app/backend/`에 있는지 확인
- `DATABASE_URL`의 user/pass가 docker-compose.yml과 일치하는지 확인
- PostgreSQL 컨테이너가 running 상태인지 `docker compose ps`로 확인

**프론트엔드 빌드 에러**
- `node_modules` 삭제 후 `npm install` 재시도
- Node.js 버전이 18 이상인지 확인

**CORS 에러 (브라우저 콘솔)**
- `.env`의 `CORS_ORIGINS`가 `http://localhost:3000`인지 확인

**스트리밍이 안 될 때**
- 백엔드 터미널에서 에러 로그 확인
- 브라우저 개발자도구 Network 탭에서 `/api/v1/chat` 요청 확인

---

## 남은 작업

### vLLM 연동 (Track 1 완료 후)

`.env` 수정만으로 전환:
```bash
LLM_MODE=vllm
LLM_BASE_URL=http://<vllm-서버-주소>/v1
LLM_MODEL=<파인튜닝된-모델-이름>
LLM_API_KEY=<필요시>
```

코드 수정 불필요.
