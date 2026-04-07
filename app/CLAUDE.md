# app/ 디렉토리 작업 지시서 (Track 2)

## 미션

파인튜닝된 Gemma 4 sLLM과 즉시 연동 가능한 채팅 웹 앱 구축.

**가장 중요한 것**: vLLM에 파인튜닝된 모델이 올라오면 환경변수 한두 개만 수정해서 동작해야 한다. 코드 수정 없이.

## 첫 작업: 코드 분석 + 보고

코드 작성 전에 **반드시 현재 상태를 분석하고 보고하라.**

### 분석 항목

1. `app/backend/` 디렉토리 구조 (tree 출력)
2. `app/frontend/` 디렉토리 구조 (tree 출력)
3. `app/backend/pyproject.toml` 또는 `requirements.txt` 내용 (의존성)
4. `app/frontend/package.json` 내용 (의존성)
5. 백엔드의 주요 파일들이 어디까지 구현되어 있는지
6. 프론트엔드의 주요 컴포넌트가 어디까지 구현되어 있는지
7. `docker-compose.yml`에 PostgreSQL, Qdrant 같은 서비스가 있는지 확인
8. Alembic 마이그레이션 디렉토리가 셋업되어 있는지

### 분석 보고 형식

```
## 현재 상태 분석

### 백엔드
- 디렉토리 구조: [tree 출력]
- 의존성: [pyproject.toml 핵심 패키지]
- 구현 완료: [완성된 파일과 기능]
- 미구현: [없는 것들]
- 발견된 이슈: [있다면]

### 프론트엔드
- 디렉토리 구조: [tree 출력]
- 의존성: [package.json 핵심 패키지]
- 구현 완료: [완성된 컴포넌트]
- 미구현: [없는 것들]

### 인프라
- docker-compose 서비스: [목록]
- DB 셋업 상태: [Alembic 등]

### 권장 작업 순서
1. ...
2. ...
```

이 보고를 출력한 다음, **사용자 승인을 기다리지 않고** 바로 첫 번째 작업으로 진행하라.
다만 아래 "사용자 확인이 필요한 작업"에 해당하는 변경은 작업 전에 반드시 확인받을 것.

## 사용자 확인이 필요한 작업

다음 작업은 실행 전에 사용자에게 확인받아라:

- 기존 파일 5개 이상 삭제
- 기존 디렉토리 구조 대규모 변경
- 의존성 패키지 제거 (추가는 OK)
- 데이터베이스 스키마 파괴적 변경 (drop, rename)
- 환경변수 이름 변경
- README, CLAUDE.md 같은 문서 파일 수정

## 기술 스택 (확정)

### Frontend
- Next.js 14+ (App Router)
- TypeScript
- Tailwind CSS
- shadcn/ui
- Redux Toolkit (이미 도입되어 있음 — 그대로 사용)
- Streaming: Fetch API + SSE

### Backend
- Python 3.12
- Poetry
- FastAPI
- PostgreSQL (docker-compose에 이미 있음)
- SQLAlchemy + Alembic
- httpx 또는 openai SDK (vLLM 호출용)
- python-dotenv (환경 변수)

### 사용 금지
- 다른 LLM SDK (LangChain, LlamaIndex 등)
- 인증 라이브러리 (JWT, OAuth 등) — Phase 1엔 인증 없음
- 단위 테스트 프레임워크 외 추가 테스트 도구
- 새로운 상태 관리 라이브러리 (Redux Toolkit 외 추가 금지)

## 핵심 설계 원칙

### 1. LLM 클라이언트는 추상화된 인터페이스

`services/llm_client.py`에 추상 클래스 + 두 구현체:

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator

class LLMClient(ABC):
    @abstractmethod
    async def stream_chat(
        self, messages: list[dict]
    ) -> AsyncIterator[str]:
        ...

class MockLLMClient(LLMClient):
    """개발용. 미리 준비한 가짜 응답을 한 글자씩 yield."""
    ...

class VLLMClient(LLMClient):
    """실제 vLLM 서버 호출. OpenAI 호환 API 사용."""
    def __init__(self, base_url: str, api_key: str, model: str):
        ...
```

환경변수 `LLM_MODE`로 어느 구현체를 쓸지 결정:
- `LLM_MODE=mock` → MockLLMClient
- `LLM_MODE=vllm` → VLLMClient

**이 구조 덕분에 vLLM 준비되면 .env만 수정하면 끝.**

### 2. OpenAI Python SDK 사용

vLLM은 OpenAI Chat Completions API와 호환되므로 `openai` SDK를 그대로 사용한다.
직접 httpx로 SSE 파싱하지 말 것 (오류 가능성 높음).

```python
from openai import AsyncOpenAI

client = AsyncOpenAI(
    base_url=settings.LLM_BASE_URL,
    api_key=settings.LLM_API_KEY,
)

stream = await client.chat.completions.create(
    model=settings.LLM_MODEL,
    messages=messages,
    stream=True,
)

async for chunk in stream:
    delta = chunk.choices[0].delta.content
    if delta:
        yield delta
```

### 3. 시스템 프롬프트는 외부 텍스트 파일

코드에 하드코딩 금지. `app/backend/prompts/` 디렉토리에 텍스트 파일로 관리:

```
app/backend/prompts/
├── nietzsche_v1.txt    # 기본 프롬프트
└── default.txt         # 폴백
```

환경변수 `SYSTEM_PROMPT_FILE`로 어느 파일 읽을지 결정.
백엔드 시작 시 메모리에 로드해서 캐시.

**Phase 1 임시 프롬프트** (실제 내용은 Track 1에서 나중에 제공):
```
당신은 사용자의 고민과 질문에 한국어로 답하는 상담자입니다.
사용자가 편안하게 대화할 수 있도록 따뜻하고 진지하게 응답하세요.
```

### 4. 환경변수 표준

`.env.example`:
```bash
# LLM 설정
LLM_MODE=mock
LLM_BASE_URL=http://localhost:8001/v1
LLM_MODEL=gemma-4-26b-a4b-nietzsche
LLM_API_KEY=dummy

# 시스템 프롬프트
SYSTEM_PROMPT_FILE=prompts/nietzsche_v1.txt

# DB
DATABASE_URL=postgresql+asyncpg://nietzsche:nietzsche@localhost:5432/nietzsche

# CORS
CORS_ORIGINS=http://localhost:3000
```

## API 설계

### POST /chat (스트리밍)

요청:
```json
{
  "conversation_id": "uuid-1234",
  "message": "회사에서 번아웃이 왔어요"
}
```

처음 보내는 경우 `conversation_id` 생략:
```json
{
  "message": "회사에서 번아웃이 왔어요"
}
```

응답: SSE 스트림

```
data: {"type": "metadata", "conversation_id": "uuid-1234"}

data: {"type": "delta", "content": "그대는"}

data: {"type": "delta", "content": " 지금"}

data: {"type": "delta", "content": " 권태의"}

data: {"type": "done"}
```

에러 발생 시:
```
data: {"type": "error", "message": "LLM 응답 생성 실패"}
```

### GET /conversations/{id}/messages

대화 복원용. 페이지 새로고침 시 사용.

응답:
```json
{
  "conversation_id": "uuid-1234",
  "messages": [
    {"role": "user", "content": "...", "created_at": "..."},
    {"role": "assistant", "content": "...", "created_at": "..."}
  ]
}
```

system 메시지는 응답에 포함하지 않음 (백엔드 내부에서만 사용).

## 백엔드 구현 흐름

### 1. /chat 엔드포인트 처리 흐름

```python
async def chat(request: ChatRequest, db: AsyncSession):
    # 1. conversation_id 처리
    if request.conversation_id is None:
        conversation = await create_conversation(db)
        conv_id = conversation.id
    else:
        conv_id = request.conversation_id
    
    # 2. user 메시지 DB 저장
    await save_message(db, conv_id, "user", request.message)
    
    # 3. 컨텍스트 조립
    system_prompt = load_system_prompt()
    history = await get_messages(db, conv_id)
    messages = [
        {"role": "system", "content": system_prompt},
        *[{"role": m.role, "content": m.content} for m in history]
    ]
    
    # 4. SSE 스트리밍
    async def event_generator():
        yield sse_event("metadata", {"conversation_id": str(conv_id)})
        
        full_response = ""
        try:
            async for delta in llm_client.stream_chat(messages):
                full_response += delta
                yield sse_event("delta", {"content": delta})
        except Exception as e:
            yield sse_event("error", {"message": str(e)})
            return
        
        await save_message(db, conv_id, "assistant", full_response)
        yield sse_event("done", {})
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

### 2. DB 스키마

```python
# models/conversation.py
class Conversation(Base):
    __tablename__ = "conversations"
    id: UUID = Column(UUID, primary_key=True, default=uuid4)
    title: str | None = Column(String, nullable=True)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    
    messages: list["Message"] = relationship("Message", back_populates="conversation")

# models/message.py
class Message(Base):
    __tablename__ = "messages"
    id: UUID = Column(UUID, primary_key=True, default=uuid4)
    conversation_id: UUID = Column(UUID, ForeignKey("conversations.id"))
    role: str = Column(String)  # "user" | "assistant"
    content: str = Column(Text)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    
    conversation: Conversation = relationship("Conversation", back_populates="messages")
```

system 메시지는 DB에 저장하지 않음 (백엔드가 매번 시스템 프롬프트 파일에서 로드).

### 3. Mock 클라이언트 구현 가이드

mock은 실제 vLLM 응답과 동일한 형태로 동작해야 한다:

```python
class MockLLMClient(LLMClient):
    async def stream_chat(self, messages: list[dict]) -> AsyncIterator[str]:
        fake_response = (
            "그대는 지금 권태의 심연을 들여다보고 있구나. "
            "하지만 권태야말로 위대한 사상이 잉태되는 자궁이다. "
            "이 무의미함을 직시하라. 그것이 그대를 더 강하게 만들 것이다."
        )
        for char in fake_response:
            yield char
            await asyncio.sleep(0.03)
```

mock 응답은 여러 개 준비해서 랜덤 또는 메시지 키워드 기반으로 선택하면 더 자연스러움.

## 프론트엔드 구현 흐름

### 1. 라우팅

```
app/
├── page.tsx                    # 새 대화 시작 (빈 채팅창)
└── chat/
    └── [conversationId]/
        └── page.tsx            # 기존 대화 로드 + 채팅
```

### 2. 첫 메시지 흐름

```
1. 사용자가 / 페이지에서 메시지 입력
2. 프론트가 POST /chat { message } 전송 (conversation_id 없음)
3. SSE 응답에서 첫 metadata 이벤트로 conversation_id 받음
4. router.replace(`/chat/${conversationId}`) — URL 업데이트
5. 스트리밍되는 delta들을 화면에 표시
6. done 이벤트로 완료
```

### 3. 후속 메시지 흐름

```
1. /chat/uuid-1234 페이지에서 메시지 입력
2. URL에서 conversation_id 추출
3. POST /chat { conversation_id, message } 전송
4. 스트리밍 표시
```

### 4. 페이지 새로고침 / 직접 URL 접근

```
1. /chat/uuid-1234 페이지 마운트
2. GET /conversations/uuid-1234/messages 호출
3. 응답을 Redux store에 로드
4. 화면에 메시지 히스토리 표시
```

### 5. UX 디테일

- 메시지 전송 즉시 user 메시지를 화면에 표시 (낙관적 업데이트)
- LLM 응답 대기 중: 인디케이터 표시 ("...")
- 첫 delta 받으면: 인디케이터 사라지고 스트리밍 시작
- 스트리밍 중에는 입력창 비활성화
- done 받으면 입력창 다시 활성화

## 디자인 가이드 (중요)

**AI스러운 디자인 절대 금지.** 사람이 디자인한 것 같은 빈티지/고전 느낌으로 가야 한다.

### 색상 팔레트 (필수 사용)

```css
--bg-primary: #f4f1ea;     /* 오프화이트 베이지 */
--bg-secondary: #e8e3d6;   /* 약간 어두운 베이지 */
--text-primary: #2c2416;   /* 다크 브라운 (거의 검정) */
--text-secondary: #6b5d4f; /* 미디엄 브라운 */
--accent: #8b2e1f;         /* 다크 와인 레드 */
--border: #c4baa9;         /* 페이드 베이지 */
```

### 절대 금지 색상
- 보라색 (#8b5cf6, #a855f7 등)
- 그라데이션 (linear-gradient, radial-gradient 모두)
- 형광/네온 색상
- 청록색 그라데이션 (cyan-to-blue 같은)
- 표준 부트스트랩/머티리얼 색상

### 타이포그래피

```css
--font-serif: Georgia, 'Times New Roman', serif;
--font-display: Georgia, serif;
```

- 본문: Georgia 16px, line-height 1.7
- 제목: Georgia 24~32px, font-weight 400 또는 500
- **산세리프 사용 금지** (UI 인풋 컴포넌트 외)

### 레이아웃

- 채팅 컨테이너: max-width 720px, 중앙 정렬
- 여백 넉넉하게 (padding 최소 24px)
- border-radius: 0~4px (둥근 모서리 최소화)
- box-shadow: 없음 또는 매우 미묘하게
- 메시지 사이 간격 충분히 (24~32px)

### 절대 금지

- 그라데이션 배경
- 둥근 카드 (border-radius 12px 이상)
- 강한 그림자 효과
- 거대한 이모지
- "AI Powered", "Powered by GPT" 같은 문구
- 네온 강조 버튼
- 다크 모드 토글 (불필요)
- 반응형 모바일 최적화 (데스크톱만 — 발표용이므로)

### 헤더 디자인

상단에 단순 헤더:
```
─────────────────────────────────────
   니체 페르소나 sLLM 상담
   캡스톤 디자인 데모
─────────────────────────────────────
```

로고 없음. 단순한 텍스트만. 헤더 아래 얇은 보더 라인.

### 채팅 메시지 스타일

- user 메시지: 우측 정렬, `bg-secondary` 배경, `text-primary` 글자
- assistant 메시지: 좌측 정렬, 배경 없음, `text-primary` 글자
- 메시지 박스는 둥근 모서리 거의 없음
- 메시지 간격은 충분히

## 작업 순서

분석 보고 후 다음 순서로 진행:

### 단계 1: 백엔드 기본 셋업
- Poetry 환경 정비 또는 셋업
- 환경변수 시스템 (`config.py`, `.env.example`)
- 시스템 프롬프트 파일 구조 (`prompts/`)
- LLM 클라이언트 추상화 + Mock 구현
- `/chat` 엔드포인트 (mock 모드로 SSE 동작)

### 단계 2: DB 통합
- PostgreSQL 연결 셋업
- SQLAlchemy 모델 (Conversation, Message)
- Alembic 마이그레이션
- conversation/message 저장 로직
- `/chat`에 conversation_id 처리 추가
- `GET /conversations/{id}/messages` 엔드포인트

### 단계 3: 프론트엔드 정리
- Next.js 라우팅 (`/`, `/chat/[id]`)
- Redux store 정리 (필요하면)
- API 클라이언트 (`lib/api.ts`)
- SSE 파싱 로직

### 단계 4: 채팅 UI 구현
- 채팅 컨테이너 컴포넌트
- 메시지 컴포넌트 (user/assistant)
- 입력창 컴포넌트
- 스트리밍 표시 + 인디케이터

### 단계 5: 디자인 적용
- 빈티지 색상 팔레트 적용
- Georgia 폰트 적용
- 헤더 추가
- 여백/간격 다듬기

### 단계 6: VLLMClient 구현
- mock과 동일 인터페이스
- openai SDK 기반
- 환경변수로 mock ↔ vllm 전환 동작 확인

### 단계 7: 통합 동작 확인
- 첫 메시지 → conversation 생성 → URL 업데이트 → 스트리밍
- 후속 메시지 → 같은 conversation에 추가
- 새로고침 → 메시지 복원
- mock 모드에서 전체 흐름 동작

## 토큰 절약 전략

각 단계는 가능하면 별도 세션으로 진행. 단계 끝나면 `/clear` 또는 새 세션 시작.
긴 세션은 `/compact` 명령으로 컨텍스트 압축.

작업 시작 시 명시적으로 파일 범위를 지정:
- "이번엔 services/llm_client.py 와 config.py 만 작업해. 다른 파일은 읽지 마."

작업 끝날 때 종료 조건을 명확히:
- "이 3가지가 끝나면 멈추고 보고해. 추가 작업 금지."

## 진행 보고 형식

각 단계 끝날 때마다 다음 형식으로 보고:

```markdown
## 단계 N 완료

### 작업한 것
- 파일1: 변경 내용
- 파일2: 변경 내용

### 동작 확인
- [확인 방법]

### 다음 단계
- [다음 작업]

### 사용자 확인 필요
- [있다면, 없으면 생략]
```

## 절대 하지 말 것

- ml/ 디렉토리 접근 (.claudeignore로 차단됨)
- 인증/회원가입 시스템 추가
- RAG 통합 (Phase 2)
- 추가 LLM SDK 도입 (LangChain 등)
- 새로운 상태관리 라이브러리 (Redux Toolkit 외)
- 다국어 지원
- 다크 모드
- 모바일 반응형 (데스크톱만)
- "혹시 모르니까" 만드는 기능
- 정교한 에러 페이지 (간단한 처리만)
- 단위 테스트 작성 (시간 낭비)
- README, 루트 CLAUDE.md 수정

## 통합 시점 (참고용)

Track 1이 vLLM에 모델 서빙 준비를 완료하면 사용자가 다음을 알려줄 것:

1. vLLM 서버 base URL
2. 모델 이름
3. 시스템 프롬프트 텍스트 파일 (있다면)

이 시점에서 `.env`만 수정하면 즉시 동작해야 함.