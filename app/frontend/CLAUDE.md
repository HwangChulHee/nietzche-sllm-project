@AGENTS.md

# Frontend — 비주얼 노벨 가이드

> Next.js 16 (App Router) + Redux Toolkit + Fetch SSE + Tailwind 4.
> 작품 결: 책 삽화 레이아웃, 세피아 토큰, 절제된 인터랙션.

---

## 라우팅 (단일 라우터: `next/navigation`)

| 라우트 | 컴포넌트 | 용도 |
|---|---|---|
| `/` | `TitleScreen` | 타이틀 + [시작]/[불러오기]/[종료] |
| `/ep1/scene/[id]` | `NarrationScreen` (id 2/3/4) / `InteractionScreen` (id 5/6/7) | Ep 1 본문 |
| `/ep1/ending` | `EndingCard` | Ep 1 #8 빈 길 |
| `/ep2/transition` | `TransitionEp2` | 카운드오버 (검은 배경 + italic) |
| `/ep2/scene/[id]` | `NarrationScreen` (id 1/2/3) / `InteractionScreen` (id 4) | Ep 2 본문 |
| `/ep2/ending` | `EndingCard` | Ep 2 엔딩 |

라우트 변경은 `useNavigate()` 훅 사용 (검은 페이드 오버레이 transition).

---

## 컴포넌트 매트릭스 (`components/vn/`)

| 컴포넌트 | 역할 |
|---|---|
| `Frame` | 16:10 책 삽화 캔버스 (vn-book) |
| `IllustrationLayer` | Next/Image 일러스트 (mode: narration 70% / interaction 50% / fullscreen) |
| `NarrationScreen` | 정적 나레이션 단락 진행 + ▼ 인디케이터 + 강조 마커 (`**...**`) + [해설] |
| `InteractionScreen` | sLLM 발화 + 학습자 입력 + 화면 전환 + 작별 흐름 |
| `MessageBox` | 인터랙션 누적 발화 (좌-차라 / 우-그대) |
| `InputArea` | textarea + 카운터 + [← 뒤로] / [발화하기] / [침묵] / [화면 전환 →] |
| `EndingCard` | 풀스크린 일러스트 + 5초 정적 → 텍스트 → 메뉴 시퀀스 |
| `TitleScreen` | 타이틀 + 메뉴 + 인용구 |
| `TransitionEp2` | Ep 1 → Ep 2 카운드오버 (검은 배경 italic) |
| `HaeseolPanel` | 우측 50% 슬라이드 패널 (정적 풀이 + [더 깊이 묻기]) |
| `Modal` | 공용 모달 (백드롭 + 평이한 시스템 톤) |
| `BackButton` | 좌하단 [← 뒤로] (narration / ending 한정) |
| `ToastHost` | uiSlice.toast 렌더 |
| `TransitionOverlay` | useNavigate의 검은 페이드 오버레이 |

---

## Redux 슬라이스 (`lib/store/`)

| 슬라이스 | 상태 |
|---|---|
| `episodeSlice` | episode / sceneIndex / mode (URL 미러) |
| `dialogueSlice` | 인터랙션 메시지 + streaming state + userTurns (resetForScreen) |
| `haeseolSlice` | 해설 패널 open + queryHistory + streaming |
| `saveSlice` | 단일 슬롯 (`SaveSlot`은 `lib/api/types`에서 re-export) |
| `uiSlice` | fade(idle/out) + toast + modal |

---

## 훅 (`lib/hooks/`)

| 훅 | 역할 |
|---|---|
| `useAppDispatch` / `useAppSelector` | 타입 추론 헬퍼 |
| `useNavigate` | 검은 페이드 오버레이 transition + router.push |
| `useInteraction(scene)` | 자동 발화 시퀀스 + send/silent/farewell + AbortController |
| `useExplain(screenId)` | [더 깊이 묻기] SSE + history 누적 + 화면 전환 시 reset |
| `useSave` | getSave/postSave/deleteSave + saveSlice 동기화 |

---

## API 클라이언트 (`lib/api/`)

- `sse.ts`: 공통 SSE 파서 (metadata/delta/done/error). AbortError silent.
- `persona.ts`: `streamRespond` / `streamRespondAuto` / `streamRespondFarewell`
- `explain.ts`: `streamExplain` — `app/ml-backend/server.mjs`의 `POST /api/v1/explain` (라이브 RAG, llama.cpp 기반)
- `summarize.ts`: `streamSummarize`
- `save.ts`: `getSave` / `postSave` / `deleteSave`
- `types.ts`: SSE 이벤트(metadata/delta/done/error) 스키마 미러

base URL은 `process.env.NEXT_PUBLIC_API_BASE` (기본 `http://localhost:3001` — ml-backend Express 래퍼).
인터랙션 페르소나·요약 sLLM은 Phase 9에서 ml-backend로 통합 예정 (현재 explain만 실 연결).

---

## 정적 데이터 (`data/`)

```
data/
├── scenes/
│   ├── types.ts                      # Paragraph / NarrationScene / InteractionScene / EndingCardData
│   ├── ep1_screen{2,3,4}_*.ts        # 정적 나레이션
│   ├── ep1_screen{5,6,7}_*.ts        # 인터랙션 메타
│   ├── ep1_screen8_ending.ts
│   ├── ep2_screen{1,2,3,4}_*.ts
│   └── ep2_ending.ts
└── haeseol/
    ├── types.ts                      # HaeseolEntry / HaeseolQuote
    ├── ep1_screen{2,3,4}_*.ts        # 정적 풀이 (사용자 작성)
    ├── ep2_screen{1,2,3}_*.ts
    └── index.ts                      # getHaeseolByScreenId 레지스트리
```

---

## 디자인 토큰 (`app/globals.css`)

`--vn-bg #f5ecd9` / `--vn-bg-darker #ebe0c8` / `--vn-ink #2a1f14` /
`--vn-ink-light #6b5f4f` / `--vn-ink-muted #b8ad9b` /
`--vn-letterbox #0d0a07` / `--vn-font-serif Georgia, Times New Roman, serif`.

본문 안 강조는 `**키워드**` 마크다운식 → `<em class="vn-emph">` 변환 (진한 잉크 + font-weight 600 + 1.08em + quote 안 italic 해제).

---

## 개발 명령

```bash
npm run dev           # 개발 서버 (포트 3000)
npm run build         # 프로덕션 빌드
npx tsc --noEmit      # 타입 체크
npm run lint          # ESLint
```

테스트 프레임워크 미도입 (캡스톤 시간 절약, VN_AGENTS §3.5 결정).

---

## 의존성 추가

```bash
npm install <패키지명>
```

신규 LLM SDK / 상태관리 라이브러리 도입은 금지 (VN_AGENTS §3.5).
