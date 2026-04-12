# Frontend — Next.js 16 앱

니체 sLLM 상담 시스템의 웹 인터페이스. Next.js 16 App Router + Redux Toolkit + SSE 스트리밍 + Tailwind 4 빈티지 디자인.

**관련 문서**:
- Next.js 16 + Redux 가이드 → [`CLAUDE.md`](./CLAUDE.md)
- Next.js 16 breaking changes 경고 → [`AGENTS.md`](./AGENTS.md)
- 전체 시스템 재현 절차 → [`../README.md`](../README.md)

---

## 실행

### 1. Node.js 환경

    export NVM_DIR=/workspace/.nvm
    source $NVM_DIR/nvm.sh 2>/dev/null
    node --version   # v20+ 이어야 함

### 2. 의존성 설치

    cd /workspace/nietzche-sllm-project/app/frontend
    npm install

### 3. 환경변수 (`.env.local`)

    NEXT_PUBLIC_API_BASE=http://localhost:8000

Cloudflare tunnel 사용 시:

    NEXT_PUBLIC_API_BASE=https://derby-xxx.trycloudflare.com

### 4. Production build + start (권장)

Dev 모드(`npm run dev`)는 Tailwind 4 + Turbopack 호환 이슈가 있어 Production 모드 사용.

    rm -rf .next
    npm run build
    npm run start

Background:

    nohup npm run start > /workspace/tmp/frontend.log 2>&1 &

### 5. 접속

    http://localhost:3000

---

## 주요 페이지

### `/` — 새 대화 시작

빈 채팅창. 니체 인용문 ("무엇이 그대를 심연으로 이끌었는가?") 표시.
첫 메시지 전송 시 `POST /api/v1/chat` → metadata 이벤트로 `conversation_id` 수신 → `router.replace("/chat/{id}")` 로 URL 자동 업데이트.

### `/chat/[conversationId]` — 기존 대화

URL에서 conversation_id 추출 → `GET /api/v1/conversations/{id}/messages` 호출 → Redux store에 로드 → 화면 표시.

후속 메시지는 같은 conversation에 추가. 페이지 새로고침 시에도 DB에서 메시지 복원.

### 공통 layout (`app/layout.tsx`)

모든 페이지가 공유하는 구조:
- 좌측: `<Sidebar />` (260px 고정)
- 우측 상단: `<Header />` (제목 + 휴지통 삭제 버튼)
- 우측 중앙: `{children}` (페이지별 메시지 영역)
- 우측 하단: `<ChatInput />` (항상 고정, footer)

---

## 컴포넌트

### `components/Sidebar.tsx`

좌측 260px 고정 사이드바.
- 상단: 제목 "니체 페르소나 sLLM" + 부제 "캡스톤 디자인 데모"
- "+ 새 대화" 버튼 → `/` 로 이동 + Redux `clearChat()` dispatch
- 가짜 최근 대화 5개 (시각적 풍부함용, 기능 없음)
- 하단: "신은 죽었다. — Friedrich Nietzsche" 캡션

### `components/Header.tsx`

상단 헤더.
- 제목 "니체 페르소나 sLLM 상담"
- 우측: 현재 대화가 있을 때만 휴지통 아이콘 (`Trash2` from lucide-react)
- 클릭 → `window.confirm()` → `deleteConversation` thunk → `router.replace("/")`

### `components/chat/ChatInput.tsx`

ChatGPT/Claude 스타일 통합 입력 컨테이너.
- 흰 배경, 1.5px border, focus 시 와인색 ring
- textarea 자동 높이 조절 (1줄 ~ 6줄)
- 우측 하단 원형 전송 버튼 (`ArrowUp` from lucide-react)
- 활성/비활성 색상 구분, hover 시 진한 와인색
- placeholder: "니체에게 질문하십시오..."
- 자체적으로 `useStreamingChat()` 호출 (prop drilling 없음)

### `components/chat/MessageBubble.tsx`

메시지 버블.
- 사용자 메시지: 우측 정렬, 진한 베이지 배경 + border, "나" 라벨
- 니체 응답: 좌측 정렬, 좌측에 3px 와인색 strip, "NIETZSCHE" 라벨 (대문자 + 와인색 + bold)
- 스트리밍 중: 와인색 커서 애니메이션

---

## 상태 관리 (Redux Toolkit)

### `lib/store/chatSlice.ts`

상태:

    interface ChatState {
      currentConversationId: string | null;
      messages: Message[];
      isStreaming: boolean;
      messagesLoading: boolean;
      error: string | null;
    }

액션 (reducers):
- `setConversation(id)` — 대화 ID 설정
- `addUserMessage(content)` — 사용자 메시지 추가 + streaming 시작
- `startAssistantMessage()` — 빈 assistant 메시지 생성
- `appendDelta(content)` — 마지막 메시지에 토큰 append
- `finishStreaming()` — streaming 플래그 해제
- `clearChat()` — 모든 상태 초기화

비동기 thunks:
- `fetchMessages(conversationId)` — `GET /conversations/{id}/messages` 호출, 대화 복원
- `deleteConversation(conversationId)` — `DELETE /conversations/{id}` 호출, 성공 시 messages=[], currentConversationId=null

### `lib/hooks/useStreamingChat.ts`

SSE 스트리밍 훅.
- `fetch + ReadableStream`으로 `/api/v1/chat` 호출
- SSE 파싱 (`data: {...}\n\n`)
- 이벤트 타입별 처리: `metadata` → setConversation + URL 업데이트, `delta` → appendDelta, `done` → finishStreaming, `error` → 에러 표시

첫 메시지 시 `router.replace("/chat/{id}")` 로 URL 자동 업데이트.

---

## 디자인 시스템

빈티지/고전 테마. 자세한 규약은 [`../CLAUDE.md`](../CLAUDE.md)의 "디자인 가이드" 섹션 참조.

### 색상 (CSS variables in `app/globals.css`)

    --bg-primary: #f4f1ea      (오프화이트 베이지)
    --bg-secondary: #e8e3d6    (약간 어두운 베이지)
    --text-primary: #2c2416    (다크 브라운)
    --text-secondary: #6b5d4f  (미디엄 브라운)
    --accent: #8b2e1f          (다크 와인 레드)
    --border-color: #c4baa9    (페이드 베이지)

### 타이포그래피

    --font-serif: Georgia, 'Times New Roman', serif

본문 16px, line-height 1.7.

### 금지 사항

- 그라데이션, 보라색, 네온 색상
- border-radius 12px 이상 (ChatInput 컨테이너의 6px 제외)
- 강한 box-shadow
- 이모지, "AI Powered" 문구
- 다크 모드, 모바일 반응형

---

## 트러블슈팅

### `npm run dev`가 CSS를 제대로 못 올림

Tailwind 4 + Next.js 16 Turbopack 호환 이슈. Production 모드 사용:

    rm -rf .next && npm run build && npm run start

### 브라우저에서 CSS가 깨져 보임 (Cloudflare tunnel)

Cloudflare Quick Tunnel이 이전 빌드의 CSS를 캐시. 새 터널 발급 후 시크릿 창으로 접속.

### Next.js 16 dev cross-origin 차단

    ⚠ Blocked cross-origin request to Next.js dev resource

`next.config.ts`에 allowedDevOrigins 추가:

    const nextConfig: NextConfig = {
      allowedDevOrigins: ["your-cloudflare-domain.trycloudflare.com"],
    };

Production 모드는 이 제약 없음.

### 메시지 보냈는데 응답 안 옴

1. DevTools Network 탭 → `/api/v1/chat` 요청 확인
2. CORS 에러면 백엔드 `.env`의 `CORS_ORIGINS=*` 확인
3. 백엔드 다운됐으면 `curl http://localhost:8000/health`
4. vLLM 다운됐으면 `curl http://localhost:8002/v1/models`

### 삭제 버튼 안 보임

`currentConversationId`가 null. 메시지를 한 번 보내서 대화가 생성된 후에만 표시.
