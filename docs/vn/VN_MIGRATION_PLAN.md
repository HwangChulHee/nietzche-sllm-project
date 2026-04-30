# VN_MIGRATION_PLAN.md — 비주얼 노벨 마이그레이션 마스터 플랜

> 옛날 상담 챗봇 (`app/`, Phase 2 완료) → 비주얼 노벨 전환 작업의 Phase 분할.
> 각 Phase = 한 세션. 결과물이 git commit 단위로 떨어지는 크기.
>
> **이 문서는 Phase별 *입력/산출물/종료 조건*을 정의한다. 디테일 정책은 `VN_UI_POLICY.md` 등 참조.**

작성일: 2026-04-30
대상: Claude Code (또는 다른 LLM 세션)

---

## 0. 핵심 흐름

```
Phase 0 (현재): 컨텍스트 준비          ← 이 세션에서 산출물 작성으로 완료
Phase 1: 저장소 정리 + 문서 push       (코드 작업 거의 X)
Phase 2: 백엔드 인터페이스 + Mock 구현  ← *vLLM 실제 호출 X. Mock만.*
Phase 3: 프론트 라우팅 + Redux 골격
Phase 4: 정적 나레이션 컴포넌트 + 텍스트 데이터
Phase 5: 책 삽화 레이아웃 + 페이드 + 일러스트 placeholder
Phase 6: 인터랙션 컴포넌트 (누적 박스 + 입력 + 화면 전환)
Phase 7: 해설 패널 + 모달 + 토스트 + 세이브 시스템
Phase 8: Ep 2 통합 + transition + 시연 시나리오 대본
─────────────────────────────────────────────────────
(추후 별도 세션) Phase 9: vLLM 실제 연결 + RAG + 요약 sLLM
```

**Phase 8까지 끝나면 Mock 모드로 *완전한 작품 시연 가능*.** Phase 9는 백엔드 결정 사항이 다 굳어진 후.

---

## 1. 살릴 자산 / 폐기할 자산 매트릭스

### 살린다 (재활용)

| 자산 | 위치 | 비고 |
|---|---|---|
| `LLMClient` 추상화 (Mock/VLLM) | `app/backend/services/llm_client.py` | 페르소나/해설/요약 sLLM에 그대로 확장 |
| SSE 스트리밍 패턴 | `app/backend/api/v1/endpoints/chat.py` | 모든 sLLM 응답에 그대로 |
| FastAPI + Poetry 셋업 | `app/backend/` | 전체 살림 |
| Next.js 16 + Redux Toolkit + TypeScript | `app/frontend/` | 셋업 살림 |
| SQLAlchemy + Alembic 패턴 | `app/backend/` | 세이브 슬롯 저장에 활용 |
| 환경변수 schema (`config.py`) | `app/backend/core/` | 확장하여 사용 |
| 시스템 프롬프트 파일 패턴 | `app/backend/prompts/` | 페르소나/해설/요약별 파일 |
| Cloudflare Quick Tunnel 운영 절차 | `app/README.md` | 그대로 |

### 폐기 / archived/로 이동

| 자산 | 위치 | 처리 |
|---|---|---|
| 챗봇 UI 컴포넌트 | `app/frontend/components/{Header, Sidebar}.tsx` | `archived/components/` |
| 챗봇 메시지 컴포넌트 | `app/frontend/components/chat/{ChatInput, MessageBubble}.tsx` | `archived/components/chat/` |
| 단일 `/chat` 엔드포인트 | `app/backend/api/v1/endpoints/chat.py` | `archived/endpoints/` 후 새 엔드포인트 작성 |
| 챗봇용 Conversation 모델 | `app/backend/models/chat.py` | `archived/models/` 후 새 모델 |
| `nietzsche_contemplative.txt` 등 옛 프롬프트 | `app/backend/prompts/` | 새 페르소나 프롬프트로 교체 (옛날 것은 `archived/prompts/`) |
| LoRA 어댑터 vLLM 설정 | `ml/finetune/outputs/` 등 | 건드리지 않음 (별도 영역) |

### 절대 건드리지 않음

- `ml/` 디렉토리 전체 (`.claudeignore` 차단)
- `app/PROGRESS.md` (Phase 2 발표 자산 — 회고 가치, 그대로 보존)

---

## 2. Phase 0 — 컨텍스트 준비 (이 세션에서 완료)

**입력**: 사용자와의 합의 (Ⅰ~Ⅶ + UI 우선 + Mock 백엔드 원칙)

**산출물**:
- `VN_AGENTS.md` (단일 진입점)
- `VN_MIGRATION_PLAN.md` (이 문서)
- `VN_UI_POLICY.md` (UI/인터랙션 정책)
- `VN_PROGRESS.md` (빈 템플릿)

**종료 조건**: 위 4개 문서가 `/mnt/user-data/outputs/`에 작성됨, 사용자가 검토 완료.

**다음**: Phase 1 (저장소 정리)

---

## 3. Phase 1 — 저장소 정리 + 문서 push

### 입력
- 위 4개 문서 (Phase 0 산출물) + 기존 `HANDOFF_CONTEXT.md`, `EP1_TEXT_AND_PROMPTS.md`, `EP1_ILLUSTRATIONS.md`, `PROJECT_PLAN_v2.md`
- 기존 저장소 상태

### 작업 영역
- 저장소 루트
- `app/frontend/`, `app/backend/` (옛 컴포넌트 archived/로 이동)
- `archived/` 신설
- 최상위 `README.md`, `CLAUDE.md`

### 산출물
1. **신규 파일 push**:
   - `VN_AGENTS.md`, `VN_MIGRATION_PLAN.md`, `VN_UI_POLICY.md`, `VN_PROGRESS.md`
   - `HANDOFF_CONTEXT.md`, `EP1_TEXT_AND_PROMPTS.md`, `EP1_ILLUSTRATIONS.md`, `PROJECT_PLAN_v2.md`
   - 위치: 저장소 루트 (또는 `docs/vn/` 등 통일된 위치 — 작업자 판단)

2. **`archived/` 디렉토리 신설** + 옛날 자산 이동:
   - `archived/components/{Header.tsx, Sidebar.tsx}` ← `app/frontend/components/`에서 이동
   - `archived/components/chat/{ChatInput.tsx, MessageBubble.tsx}` ← 이동
   - `archived/prompts/{nietzsche_v1.txt, nietzsche_contemplative.txt, default.txt}` ← 이동

3. **새 README.md 작성**: 비주얼 노벨 컨셉으로 전면 교체. 옛 README는 `archived/README_legacy.md`로 백업.

4. **새 최상위 `CLAUDE.md` 작성**: Track 1/2 분리 → 비주얼 노벨 단일 작업 영역으로 교체. 옛것은 `archived/CLAUDE_legacy.md`.

5. **`VN_PROGRESS.md`에 Phase 1 완료 라인 추가**

### 종료 조건
- [ ] `git status` clean (모든 변경 commit)
- [ ] `archived/` 디렉토리에 옛 컴포넌트/프롬프트 모두 이동됨
- [ ] 새 `README.md`가 비주얼 노벨 컨셉을 반영
- [ ] `VN_PROGRESS.md`에 한 줄 추가됨
- [ ] **기존 `app/PROGRESS.md`는 그대로 유지** (회고 자산)

### 사용자 확인 필요
- README.md, CLAUDE.md 수정 — 작업 전 사용자에게 *변경 후 핵심 메시지* 한 단락 보여주고 승인 받기
- `archived/` 위치/이름 (`legacy/`로 할지, `archived/`로 할지 등)

### 다음
Phase 2 — 백엔드 인터페이스 + Mock 구현

---

## 4. Phase 2 — 백엔드 인터페이스 정의 + Mock 구현

### 입력
- `VN_UI_POLICY.md` §8 컴포넌트 매트릭스 + §1 화면 매트릭스
- `EP1_TEXT_AND_PROMPTS.md` §0~§4 (sLLM 호출 종류, 시스템 프롬프트 구조)
- 기존 `app/backend/services/llm_client.py` (재활용 베이스)

### 작업 영역
- `app/backend/api/v1/endpoints/` (새 엔드포인트)
- `app/backend/services/` (새 클라이언트 추상화)
- `app/backend/models/` (세이브 슬롯 모델)
- `app/backend/prompts/` (새 시스템 프롬프트 파일)
- `app/backend/core/config.py` (환경변수 추가)

### 산출물

**1. 엔드포인트 스펙 정의 + Mock 구현**:

| 엔드포인트 | 용도 | Mock 동작 |
|---|---|---|
| `POST /api/respond` | 페르소나 sLLM (인터랙션 #5~#7, Ep 2 #4) | 화면별/턴별 미리 짠 응답 풀에서 SSE 스트리밍 |
| `POST /api/respond/auto` | 화면 진입 시 자동 발화 | 화면별 첫 발화 고정 텍스트 스트리밍 |
| `POST /api/respond/farewell` | [작별을 고한다] 클릭 시 마지막 발화 | 미리 짠 작별 텍스트 스트리밍 |
| `POST /api/explain` | 해설 모드 동적 풀이 | 미리 짠 평이한 해설 텍스트 스트리밍 |
| `POST /api/summarize` | 세이브 시점 요약 + Ep 1→Ep 2 카운드오버 | 미리 짠 요약 1인칭 회상 텍스트 |
| `GET /api/save` | 세이브 슬롯 조회 | DB에서 단일 슬롯 |
| `POST /api/save` | 세이브 (덮어쓰기) | DB upsert + 요약 호출 |
| `DELETE /api/save` | 세이브 삭제 (불러오기 모달 [돌아가기]에선 안 씀, 미래 확장용) | DB delete |

**2. 추상화 클래스**:
```python
# app/backend/services/sllm_clients.py (또는 분리)

class PersonaClient(LLMClient): ...    # /api/respond, /api/respond/auto, /api/respond/farewell
class ExplainClient(LLMClient): ...    # /api/explain
class SummaryClient(LLMClient): ...    # /api/summarize

# 각각 Mock/VLLM 구현체. LLM_MODE=mock이면 Mock, vllm이면 VLLM.
```

**3. 환경변수 추가** (`config.py`):
```bash
LLM_MODE=mock                                  # 기본값
PERSONA_PROMPT_FILE=prompts/persona_v1.txt
EXPLAIN_PROMPT_FILE=prompts/explain_v1.txt
SUMMARY_PROMPT_FILE=prompts/summary_v1.txt
VLLM_BASE_URL=http://localhost:8002/v1         # Phase 9에서만 의미
VLLM_MODEL=gemma-4-31b-base
```

**4. 시스템 프롬프트 파일 작성** (`app/backend/prompts/`):
- `persona_v1.txt` — `EP1_TEXT_AND_PROMPTS.md` §1 + §2 풀버전 (페르소나 + 시공간 + 발화 스타일 + 시대 외 가이드)
- `explain_v1.txt` — `VN_UI_POLICY.md` §4 동적 풀이 시스템 프롬프트 + 화면별 컨텍스트 슬롯
- `summary_v1.txt` — `EP1_TEXT_AND_PROMPTS.md` §3 요약 시스템 프롬프트

**5. Mock 응답 데이터** (`app/backend/services/mock_data.py`):
```python
PERSONA_REPLIES = {
  "ep1_screen5_meeting": [...],   # 시연 위젯에서 사용한 응답들
  "ep1_screen6_walking": [...],
  "ep1_screen7_market": [...],
  "ep2_screen4_reunion": [...],
  ...
}
PERSONA_SILENT_REPLIES = [...]
PERSONA_AUTO_FIRST = {
  "ep1_screen5_meeting": "그대.\n어디서 왔는가.",  # 고정
  "ep1_screen6_walking": "...",                  # 시스템 프롬프트가 알아서 (Mock에선 미리 짠 것)
  "ep1_screen7_market": "...",
  "ep2_screen4_reunion": "그대였구나.",
}
PERSONA_FAREWELL = {...}
EXPLAIN_RESPONSES = {
  "ep1_screen2_summit": "이 화면은 ... ~입니다.",
  ...
}
SUMMARY_TEMPLATE = "그가 무엇을 짊어지고 왔는지 나는 알지 못한다..."
```

**6. SQLAlchemy 모델** (`app/backend/models/save.py`):
```python
class SaveSlot(Base):
    __tablename__ = "save_slots"
    id: int = Column(Integer, primary_key=True)  # 1슬롯이라 항상 1
    episode: str = Column(String)                # "ep1" or "ep2"
    scene_index: int = Column(Integer)           # 화면 #
    summary: str = Column(Text)                  # 요약 sLLM 출력
    recent_messages: str = Column(Text)          # JSON 직렬화
    timestamp: datetime = Column(DateTime, default=datetime.utcnow)
```

**7. Alembic 마이그레이션** 추가 (기존 패턴 따라).

### 종료 조건
- [ ] 위 8개 엔드포인트가 모두 `LLM_MODE=mock`에서 동작 (curl로 검증)
- [ ] `LLM_MODE=vllm`은 시도하지 않음 (Phase 9에서)
- [ ] 시스템 프롬프트 3개 파일이 `EP1_TEXT_AND_PROMPTS.md`에 부합
- [ ] DB 마이그레이션 적용됨
- [ ] `VN_PROGRESS.md`에 Phase 2 완료 라인

### 사용자 확인 필요
- 새 엔드포인트 URL 패턴 (`/api/respond/auto` 같은 이름) — 한 번 보고 승인
- DB 스키마 변경 (옛 `Conversation` 모델 archived/로 이동 + `SaveSlot` 신설)

### 다음
Phase 3 — 프론트 라우팅 + Redux 골격

---

## 5. Phase 3 — 프론트 라우팅 + Redux 골격

### 입력
- `VN_UI_POLICY.md` §1 화면 매트릭스 + §8 컴포넌트 매트릭스
- 기존 `app/frontend/lib/store/chatSlice.ts` (재활용 패턴)
- `app/frontend/lib/hooks/useStreamingChat.ts` (SSE 패턴 재활용)

### 작업 영역
- `app/frontend/app/` (라우팅)
- `app/frontend/lib/store/` (Redux slices)
- `app/frontend/lib/api/` 신설 (백엔드 호출)

### 산출물

**1. 라우팅 구조**:
```
app/
├── page.tsx                       # 타이틀 화면 (#1)
├── load/page.tsx                  # 불러오기 모달 (라우트 또는 모달 컴포넌트로)
├── ep1/
│   ├── scene/[id]/page.tsx        # #2~#7 동적 라우팅
│   └── ending/page.tsx            # #8
├── ep2/
│   ├── transition/page.tsx        # Ep 1 → Ep 2 카운드오버
│   ├── scene/[id]/page.tsx        # #1~#4
│   └── ending/page.tsx
└── layout.tsx                     # 전역 레이아웃 (frame 16:10)
```

**2. Redux slices**:
- `episodeSlice` — 현재 episode (`ep1`/`ep2`), scene_index, mode (`narration`/`interaction`/`title`/`ending`)
- `dialogueSlice` — 인터랙션 화면 메시지 누적 (화자, 본문, isSilent)
- `haeseolSlice` — 해설 패널 상태 (열림/닫힘, 동적 풀이 누적)
- `saveSlice` — 세이브 슬롯 상태
- `uiSlice` — 페이드 상태, 토스트, 모달

**3. API 클라이언트** (`lib/api/`):
```ts
async function streamRespond(screenId, userMessage, onDelta, onDone)  // SSE
async function streamRespondAuto(screenId, onDelta, onDone)            // SSE
async function streamRespondFarewell(screenId, onDelta, onDone)        // SSE
async function streamExplain(screenId, query, history, onDelta, onDone)// SSE
async function getSave(): Promise<SaveSlot | null>
async function postSave(payload): Promise<void>
```

**4. 페이드 transition 시스템**:
- 라우터 변경 시 페이드 효과 (Next.js App Router의 layout transition 또는 framer-motion 도입 고려 — 후자는 의존성 추가니 사용자 확인)

### 종료 조건
- [ ] 모든 라우트가 *빈 페이지*로 마운트 (정적 placeholder)
- [ ] Redux store가 Provider로 감싸짐, 기본 액션 dispatch 가능
- [ ] API 클라이언트가 백엔드 Mock 엔드포인트 호출하면 SSE 스트림 받음 (콘솔 로그로 검증)
- [ ] 페이드 transition 동작 (빈 페이지 사이 600ms 페이드)
- [ ] `VN_PROGRESS.md`에 Phase 3 완료 라인

### 사용자 확인 필요
- framer-motion 등 페이드 라이브러리 도입 여부 (또는 CSS 트랜지션만으로 처리)
- 라우팅 구조 (`/ep1/scene/2` vs `/ep1/2` 같은 변형)

### 다음
Phase 4 — 정적 나레이션 컴포넌트

---

## 6. Phase 4 — 정적 나레이션 컴포넌트 + 텍스트 데이터

### 입력
- `VN_UI_POLICY.md` §2 (정적 나레이션 정책 전부)
- `EP1_TEXT_AND_PROMPTS.md` §5 화면 #1~#4, #8 (정적 텍스트 본문)
- (Ep 2 #1~#3 텍스트는 Phase 8에서 처리 — 현재는 미작성)

### 작업 영역
- `app/frontend/components/vn/NarrationScreen.tsx` (신규)
- `app/frontend/components/vn/EndingCard.tsx` (신규)
- `app/frontend/components/vn/TitleScreen.tsx` (신규)
- `app/frontend/data/scenes/` (신규) — 정적 텍스트 데이터

### 산출물

**1. `NarrationScreen` 컴포넌트**:
- props: `paragraphs: string[]`, `enableHaeseol: boolean`, `onComplete: () => void`
- 단락 교체 페이드 (300ms)
- 클릭 / Space / Enter → 다음 단락
- 마지막 단락 후 클릭 → `onComplete()` 호출
- 우하단 ▼ 인디케이터 (블링크)
- 좌하단 [해설] 버튼 (`enableHaeseol=true`일 때만, 클릭 시 `HaeseolPanel` 마운트 — Phase 7에서 구현, 지금은 placeholder)

**2. `EndingCard` 컴포넌트**:
- props: `episode: string`, `title: string`, `body: string[]`, `actions: ActionButton[]`
- 일러스트 풀스크린 → 5초 정적 → 텍스트 페이드인 → 3초 후 메뉴 페이드인
- Ep 1 #8: 액션 = `[Ep 2로 계속]`, `[타이틀로]`
- Ep 2 엔딩: 액션 = `[Ep 3는 확장 비전 슬라이드로 대체]`, `[타이틀로]`

**3. `TitleScreen` 컴포넌트**:
- props: `onStart`, `onLoad`, `onExit`, `hasSavedSlot`
- 타이틀 "차라투스트라" + 부제 "EPISODE 1 — 하산"
- 메뉴: `[시작]`, `[불러오기]` (세이브 없으면 disabled), `[종료]`
- 인용구 "그대들에게 인간이란 무엇인가? 극복되어야 할 무엇이다."

**4. 정적 텍스트 데이터**:
- `data/scenes/ep1_screen2_summit.ts` — 단락 5개 (`EP1_TEXT_AND_PROMPTS.md` §5 #2)
- `data/scenes/ep1_screen3_forest.ts` — 단락 6개 (#3)
- `data/scenes/ep1_screen4_road.ts` — 단락 3개 (#4)
- `data/scenes/ep1_screen8_ending.ts` — 엔딩 카드 텍스트 (#8 변경분 — `[Ep 2로 계속]`/`[타이틀로]`)

### 종료 조건
- [ ] Ep 1 #1, #2, #3, #4, #8이 *클릭으로 진행되는* 작품 골격으로 동작
- [ ] [해설] 버튼은 *placeholder만* (클릭 시 토스트 *"Phase 7에서 구현"*)
- [ ] 일러스트는 placeholder SVG (Phase 5에서 본격 통합)
- [ ] 키보드 단축키 (Space/Enter) 동작
- [ ] `VN_PROGRESS.md`에 Phase 4 완료 라인

### 사용자 확인 필요
- 데이터 파일 경로 (`data/scenes/` vs `lib/scenes/` 등)

### 다음
Phase 5 — 책 삽화 레이아웃 + 페이드 시스템 + 일러스트 통합

---

## 7. Phase 5 — 책 삽화 레이아웃 + 페이드 + 일러스트 placeholder

### 입력
- `VN_UI_POLICY.md` §2.4 페이드 타이밍
- `EP1_ILLUSTRATIONS.md` 전체 (8장 가이드)
- 데모 위젯의 SVG placeholder (참고용)

### 작업 영역
- `app/frontend/components/vn/Frame.tsx` (신규) — 16:10 책 삽화 프레임
- `app/frontend/components/vn/IllustrationLayer.tsx` (신규) — 상단 일러스트 영역
- `app/frontend/components/vn/TextLayer.tsx` (신규) — 하단 텍스트 영역
- `app/frontend/public/illustrations/` (신규) — 일러스트 파일
- `app/frontend/styles/vn.css` (신규) — 세피아 토큰

### 산출물

**1. `Frame` 컴포넌트**:
- 16:10 비율 풀스크린
- 세피아 #f5ecd9 배경
- 우상단 메뉴 영역 (`children` 슬롯)
- 좌하단 인터랙션 영역 (`children` 슬롯)
- 페이드 transition (mode 변경 시 600ms, #4→#5는 800ms)

**2. `IllustrationLayer`**:
- props: `imagePath: string`, `mode: "narration" | "interaction"` (비율 결정)
- narration mode: 상단 70%
- interaction mode: 상단 50%
- placeholder 일러스트 8장 (Ep 1) + 4장 (Ep 2) 임시 SVG

**3. 디자인 토큰** (`vn.css`):
```css
:root {
  --vn-bg: #f5ecd9;
  --vn-bg-darker: #ebe0c8;
  --vn-ink: #2a1f14;
  --vn-ink-light: #6b5f4f;
  --vn-ink-muted: #b8ad9b;
  --vn-font-serif: Georgia, 'Times New Roman', serif;
}
```

**4. 일러스트 파일**:
- `screen_01_title.png` ~ `screen_08_ending.png` (Ep 1)
- `ep2_screen_01_market.png` ~ `ep2_screen_04_reunion.png` (Ep 2)
- 임시 placeholder는 SVG 또는 단순 흑백 도레 풍 이미지 (생성 도구 사용 또는 외주)
- 실제 일러스트 통합은 Phase 8 마무리에서

**5. Phase 4의 `NarrationScreen`/`EndingCard`/`TitleScreen`을 `Frame` + `IllustrationLayer` 위에 올림** — 기존 컴포넌트 리팩터링.

### 종료 조건
- [ ] Ep 1 #1~#4, #8이 책 삽화 레이아웃으로 동작
- [ ] 페이드 타이밍 정확 (#4 → #5 800ms 등)
- [ ] 디자인 토큰이 `vn.css`에 통일됨
- [ ] `VN_PROGRESS.md`에 Phase 5 완료 라인

### 사용자 확인 필요
- 일러스트 placeholder 생성 방식 (SVG / 외부 생성 도구 / 임시 흰 박스 + 라벨만)
- 일러스트 파일 위치 (`public/` vs `assets/`)

### 다음
Phase 6 — 인터랙션 컴포넌트

---

## 8. Phase 6 — 인터랙션 컴포넌트 (#5~#7, Ep 2 #4)

### 입력
- `VN_UI_POLICY.md` §3 (인터랙션 정책 전부)
- `EP1_TEXT_AND_PROMPTS.md` §5 #5~#7 (sLLM 호출 컨텍스트)
- 데모 위젯 `ep1_screen5_meeting_interaction_demo` (참고)

### 작업 영역
- `app/frontend/components/vn/InteractionScreen.tsx` (신규)
- `app/frontend/components/vn/MessageBox.tsx` (신규)
- `app/frontend/components/vn/InputArea.tsx` (신규)
- `app/frontend/lib/hooks/useInteraction.ts` (신규)

### 산출물

**1. `InteractionScreen` 컴포넌트**:
- props: `screenId: string`, `transitionLabel: string`, `onTransition: () => void`
- 진입 시 자동 발화 시퀀스 (200ms 정적 → 화자명 페이드인 → 본문 스트리밍)
- `MessageBox` + `InputArea` 자식
- 스트리밍 중 입력/전환 비활성

**2. `MessageBox`**:
- 누적 스크롤
- 차라투스트라/학습자 시각 분리 (좌-진한 / 우-옅은)
- [침묵] 메시지 italic + "…"
- 자동 스크롤 (수동 스크롤 시 일시 정지)

**3. `InputArea`**:
- textarea (자동 높이, 500자 제한, 카운터)
- [발화하기] / [침묵] / 화면 전환 버튼
- Enter 전송 / Shift+Enter 줄바꿈
- 빈 입력 [발화하기] 비활성, [침묵]은 항상 활성
- 스트리밍 중 placeholder *"…"*

**4. `useInteraction` 훅**:
- 백엔드 SSE 호출 (`streamRespond`, `streamRespondAuto`)
- 메시지 누적 → Redux dispatch
- 스트리밍 상태 관리 (BOOTING / STREAMING / IDLE)
- 화면 전환 활성 조건 체크 (응답 완료 + 학습자 발화 ≥ 1)
- 3초 지연 시 *"…"* 인디케이터

**5. 화면 전환 로직**:
- [그와 함께 걷는다 →] 클릭 → 페이드아웃 → `/ep1/scene/6` 라우트 이동 → 자동 발화
- [시장이 가까워진다 →] → `/ep1/scene/7`
- [작별을 고한다 →] → 마지막 작별 발화 sLLM 호출 → 학습자 마지막 응답 1회 → `/ep1/ending` (또는 Ep 2 #4의 경우 Ep 2 엔딩)

### 종료 조건
- [ ] Ep 1 #5 → #6 → #7 → #8 흐름이 Mock 모드로 완전 동작
- [ ] [침묵] 클릭 시 즉시 응답 스트리밍
- [ ] 화면 전환 버튼 활성/비활성 조건 정확
- [ ] 스크롤 / 자동 스크롤 / 페이드 모두 동작
- [ ] `VN_PROGRESS.md`에 Phase 6 완료 라인

### 사용자 확인 필요
- 자동 스크롤 정책 디테일 (수동 스크롤 일시 정지 구현 복잡도)

### 다음
Phase 7 — 해설 패널 + 모달 + 토스트 + 세이브 시스템

---

## 9. Phase 7 — 해설 패널 + 모달 + 토스트 + 세이브 시스템

### 입력
- `VN_UI_POLICY.md` §4 (해설 모드) + §6 (세이브 시스템)
- 데모 위젯 `ep1_save_system_demo`, `ep1_screen2_narration_demo` 해설 패널 부분 (참고)

### 작업 영역
- `app/frontend/components/vn/HaeseolPanel.tsx` (신규)
- `app/frontend/components/vn/Modal.tsx` (신규, 공용)
- `app/frontend/components/vn/Toast.tsx` (신규, 공용)
- `app/frontend/data/haeseol/` (정적 풀이 손글씨 데이터)
- `app/frontend/lib/hooks/useSave.ts` (신규)
- `app/frontend/lib/hooks/useExplain.ts` (신규)

### 산출물

**1. `HaeseolPanel`**:
- 우측 슬라이드 (380ms ease, 50% 폭)
- 정적 풀이 (위, 화면별 데이터 파일에서 로드)
- 동적 풀이 (입력창 + 누적 응답)
- ESC / [해설 닫기] 닫기
- 화면 전환 시 동적 풀이 누적 초기화

**2. `Modal` (공용)**:
- props: `title`, `body`, `actions[]`
- 백드롭 (rgba(0,0,0,0.45))
- frame 내부 absolute (position fixed X)
- 평이한 시스템 톤 (작품 결 X)

**3. `Toast` (공용)**:
- props: `message`, `duration`
- 화면 중앙 또는 상단
- 페이드 인/아웃 (200ms)

**4. 정적 풀이 데이터**:
- `data/haeseol/ep1_screen2_summit.ts` — 200~350자 손글씨
- `data/haeseol/ep1_screen3_forest.ts`
- `data/haeseol/ep1_screen4_road.ts`
- (Ep 2 #1~#3은 Phase 8에서)

**5. `useSave` 훅**:
- `getSave()`, `postSave(payload)` API 호출
- 모달 플로우 (세이브 첫 저장 / 덮어쓰기 / 불러오기)

**6. `useExplain` 훅**:
- `streamExplain` SSE 호출
- 동적 풀이 누적 (현재 화면 한정)
- 화면 전환 시 초기화

### 종료 조건
- [ ] Ep 1 #2~#4 [해설] 클릭 → 패널 슬라이드 → 정적 풀이 표시 → [더 깊이 묻기] 동작 (Mock 응답 스트리밍)
- [ ] #5~#7 [세이브] 클릭 → 모달 또는 즉시 토스트 (기존 슬롯 여부에 따라)
- [ ] #1 [불러오기] 클릭 → 슬롯 모달 → 불러오기 동작 (저장된 화면으로 점프)
- [ ] 모달 톤이 평이 (*"불러오기"*, *"저장"*)
- [ ] 출처 표기 옅게 표시 (Mock 응답에 *"참고: ..."* 한 줄)
- [ ] `VN_PROGRESS.md`에 Phase 7 완료 라인

### 사용자 확인 필요
- 정적 풀이 손글씨 (3화면 분량) 사용자가 직접 작성할지, Phase 7에서 임시로 작성 후 사용자가 다듬을지

### 다음
Phase 8 — Ep 2 통합 + transition + 시연 시나리오

---

## 10. Phase 8 — Ep 2 통합 + transition + 시연 시나리오

### 입력
- `VN_UI_POLICY.md` §7 (Ep 2 축약 정책)
- 사용자 작성 Ep 2 텍스트 (위버멘쉬 선포 / 광대 사건 등 — 이 Phase 시작 전에 사용자가 작성해야 함)
- Phase 1~7 결과물

### 작업 영역
- `app/frontend/data/scenes/ep2_*.ts` (Ep 2 텍스트 데이터)
- `app/frontend/data/haeseol/ep2_*.ts` (Ep 2 정적 풀이)
- `app/frontend/components/vn/TransitionEp2.tsx` (신규)
- `app/frontend/app/ep2/transition/page.tsx`
- `app/frontend/app/ep2/scene/[id]/page.tsx`
- `app/frontend/app/ep2/ending/page.tsx`
- `demo/scenario_script.md` (시연 대본)

### 산출물

**1. Ep 2 정적 텍스트 데이터** (3화면 + 엔딩):
- `ep2_screen1_market_arrival.ts`
- `ep2_screen2_uebermensch.ts` — *"나는 그대들에게 위버멘쉬를 가르치노라..."*
- `ep2_screen3_clown_fall.ts` — *"인간은 짐승과 위버멘쉬 사이에 매인 밧줄이다..."*
- `ep2_ending.ts`

**2. Ep 2 정적 풀이 데이터** (3화면, 사용자 작성):
- `ep2_haeseol_*.ts`

**3. `TransitionEp2` 컴포넌트**:
- 검은 배경 페이드 (600ms)
- 잉크색 옅은 글씨 페이드인 *"밤이 깊었다. 시간은 흘러, 시장의 새벽이 왔다."*
- 3초 정적
- 백그라운드에서 `streamSummarize` 호출 (Promise)
- 페이드아웃 → Ep 2 #1 페이드인
- failover: 30초 초과 시 요약 없이 Ep 2 진입

**4. Ep 2 라우팅 통합**:
- Ep 1 #8 [Ep 2로 계속] → `/ep2/transition` → `/ep2/scene/1` → ... → `/ep2/scene/4` → `/ep2/ending`
- 모든 화면이 Phase 4~7의 컴포넌트 재활용

**5. 시연 시나리오 대본** (`demo/scenario_script.md`):
- 5분 영상 시간표 (`HANDOFF_CONTEXT.md` 참조)
- 학습자 입력 미리 짠 대사
- 침묵 시연 포함
- 음성 내레이션 텍스트

**6. 일러스트 12장 최종 통합**:
- placeholder → 실제 일러스트 (생성 또는 외주 산출물)

### 종료 조건
- [ ] Ep 1 → Ep 2 → Ep 2 엔딩 전체 흐름이 Mock 모드로 동작
- [ ] transition 3초 정적 + 백그라운드 요약 호출 검증
- [ ] 시연 대본대로 5분 안에 끝까지 시연 가능
- [ ] 일러스트 12장 통합
- [ ] `VN_PROGRESS.md`에 Phase 8 완료 라인 + *"Mock 모드로 발표 데모 가능 상태"*

### 사용자 확인 필요
- Ep 2 텍스트 본문 (사용자가 미리 작성)
- 시연 대본 학습자 발화 시나리오 (사용자 검토)

### 다음
**Phase 9 (별도 세션)** — vLLM 실제 연결

---

## 11. Phase 9 (참고) — vLLM 실제 연결

> 이 Phase는 *백엔드 결정 사항이 다 굳어진 후* 별도 세션에서. 본 마이그레이션 플랜의 *바깥*.

**작업 개요**:
- `LLM_MODE=vllm`으로 swap
- `VLLMClient` 구현 (기존 Phase 2의 추상화 위에)
- vLLM 서버 띄우기 (Gemma 4 31B, 베이스 모델 — LoRA 어댑터 X)
- RAG 인덱스 구축 (BGE-M3 + 단일 인덱스 + 시간 메타 태그)
- HyDE 구현
- 풀이 RAG / 개인화 RAG 통합
- 요약 sLLM 검증
- Cloudflare Quick Tunnel 운영

**전제**: Phase 8까지 Mock 모드로 완성된 작품이 있어서, vLLM 응답 품질만 *swap-in*하여 검증.

---

## 12. 위험 신호 / 안티 패턴

각 Phase 작업 중 다음이 보이면 멈춰야 함:

- **컨셉 재뒤집기**: 세 모드 / 시간 흐름 / Ep 1+2 범위. 가볍게 뒤집지 말 것.
- **기능 욕심**: 다섯 결 분류기, 후기 저작 RAG (인터랙션 모드에), 시간 의식, 자동 세이브, 라우터 sLLM. 이미 폐기된 자산.
- **과설계**: 한 Phase 안에서 *완벽한 추상화* 시도. Mock으로 동작 우선.
- **vLLM 일찍 손대기**: Phase 8까지는 Mock만. 30B 띄우려는 욕구 참기.
- **ml/ 디렉토리 진입**: `.claudeignore` 차단됨. 절대 X.
- **archived/ 안 파일 수정**: 회고용 보존 자산. 건드리면 발표 자료 손실.

---

## 13. 변경 이력

- 2026-04-30: 초안 작성. Phase 0~9 분할. UI 우선 + Mock 백엔드 원칙 명시.
