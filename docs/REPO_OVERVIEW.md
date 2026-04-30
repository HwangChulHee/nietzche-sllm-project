# REPO_OVERVIEW.md — 외부 LLM 세션용 저장소 컨텍스트

> 이 문서 *한 파일*만 읽으면 웹 Claude / ChatGPT / 다른 LLM 세션이 본 저장소를 전체적으로 파악할 수 있도록 압축한 인덱스.
> 더 깊은 작업이 필요하면 §6 *시나리오별 함께 업로드할 파일* 표에 따라 추가 파일을 골라 업로드.

작성일: 2026-05-01
대상: 외부 LLM (파일 시스템 접근 없음)

---

## 1. 30초 컨텍스트

**프로젝트**: *"차라투스트라와의 동행"* — 학부 캡스톤 비주얼 노벨. 니체 『차라투스트라는 이렇게 말했다』 서문을 학습자가 차라투스트라 페르소나 sLLM과 함께 따라가는 인터랙티브 철학 소설.

**현재 상태 (2026-05-01)**:
- Phase 1~8 완료. Mock 모드로 Ep 1 + Ep 2 풀 사이클이 라이브.
- Phase 9 (vLLM 실 연결 + RAG)는 RunPod 환경 의존 별도 작업.
- 5월 말 최종 발표 예정.

**리포지토리**: `github.com/HwangChulHee/nietzche-sllm-project` (브랜치 `main`).

---

## 2. 핵심 개념 (작품 / 기술 동시)

### 작품 — 세 모드
| 모드 | 설명 | 화면 |
|---|---|---|
| 정적 나레이션 | 미리 작성된 본문이 클릭으로 진행 | Ep 1 #2~#4, #8 / Ep 2 #1~#3, 엔딩 |
| 인터랙션 | 차라투스트라 페르소나 sLLM과 실시간 대화 | Ep 1 #5~#7 / Ep 2 #4 |
| 해설 | 외부 해설자 sLLM이 현 화면을 평이한 한국어로 풀이 | 정적 나레이션 화면 한정 |

### 작품 — 화면 구성
- **Ep 1 (8화면)**: 타이틀 → 산 정상 → 숲의 성자 → 길로 나섬 (신의 죽음) → 만남 → 동행 → 시장 원경 → 빈 길(엔딩)
- **Ep 2 축약 (4화면 + 엔딩)**: 시장 광장 도착 → 위버멘쉬 선포 → 광대 사건 → 학습자 재회 → 엔딩
- **Ep 3 이후**: 확장 비전 슬라이드로 대체 (캡스톤 범위 밖)

### 기술 — 모드 토글
- 백엔드 sLLM은 `MockClient` / `VLLMClient` 두 구현체.
- `LLM_MODE=mock` (기본, 시연 안정성) / `LLM_MODE=vllm` (Phase 9, 실제 추론).
- 환경변수만 바꾸면 swap. 코드 수정 X.

### 기술 — 책 삽화 레이아웃
- 16:10 풀스크린 캔버스 + viewport 검은 letterbox.
- 정적 나레이션: 일러스트 70% / 텍스트 30% 분할.
- 인터랙션: 일러스트 50% / 메시지+입력 50% 분할.
- 엔딩/타이틀: 풀스크린 일러스트 + veil + 텍스트 오버레이.

---

## 3. 디렉토리 지도

```
nietzsche-project/
├── README.md                  # 프로젝트 개요 + Quick Start
├── CLAUDE.md                  # Claude Code 단일 진입점 라우터
│
├── docs/
│   ├── REPO_OVERVIEW.md       # ← 이 문서 (외부 LLM용)
│   └── vn/                    # 비주얼 노벨 작업 단일 진실 소스
│       ├── VN_AGENTS.md       # Claude Code 진입점 (행동 규약)
│       ├── VN_MIGRATION_PLAN.md   # Phase 0~9 분할 정의
│       ├── VN_UI_POLICY.md    # UI/인터랙션 규약
│       ├── VN_PROGRESS.md     # 누적 진행 로그 (Phase 8까지)
│       ├── HANDOFF_CONTEXT.md # 컨셉 전체 요약 + 폐기/유지 매트릭스
│       ├── EP1_TEXT_AND_PROMPTS.md  # Ep 1 본문 + sLLM 프롬프트
│       ├── EP1_ILLUSTRATIONS.md     # 일러스트 가이드
│       └── PROJECT_PLAN_v2.md       # 기획 마스터
│
├── app/
│   ├── README.md              # 시연 셋업 + 12화면 시연 흐름
│   ├── CLAUDE.md              # app/ 라우터 (얇음)
│   ├── PROGRESS.md            # 4/13 중간 발표 회고 (수정 금지)
│   │
│   ├── frontend/              # Next.js 16 — 비주얼 노벨 UI
│   │   ├── README.md          # 실행 + 화면 라우팅 매트릭스
│   │   ├── CLAUDE.md          # 컴포넌트 14종 + Redux 5 슬라이스 + 훅 5 + 디자인 토큰
│   │   ├── AGENTS.md          # Next.js 16 breaking changes 경고
│   │   ├── app/               # App Router 페이지 (/, /ep1/*, /ep2/*)
│   │   ├── components/vn/     # VN 전용 컴포넌트
│   │   ├── data/scenes/       # 정적 텍스트 + 인터랙션 메타
│   │   ├── data/haeseol/      # 정적 풀이 (해설 패널)
│   │   ├── lib/api/           # SSE 클라이언트
│   │   ├── lib/hooks/         # useInteraction / useExplain / useSave / useNavigate
│   │   ├── lib/store/         # Redux slices
│   │   └── public/illustrations/  # WebP 일러스트 13장 (Ep 1 8 + Ep 2 5)
│   │
│   └── backend/               # FastAPI — sLLM 라우팅 + 세이브
│       ├── README.md          # 8개 엔드포인트 + 환경변수 + 트러블슈팅
│       ├── CLAUDE.md          # 레이어 책임 + sLLM 클라이언트 ABC
│       ├── BACKEND_STRUCTURE.md   # 아키텍처 도해 + 데이터 흐름
│       ├── api/v1/endpoints/  # respond / explain / summarize / save
│       ├── services/          # llm_client (저수준), sllm_clients (3종)
│       ├── prompts/           # 시스템 프롬프트 3개
│       ├── models/save.py     # SaveSlot (단일 슬롯)
│       └── alembic/           # DB 마이그레이션
│
├── demo/
│   └── scenario_script.md     # 발표 시연 대본 (~10분)
│
├── archived/                  # 회고 자산 (수정 금지)
│   ├── README_legacy.md       # 옛 상담 챗봇 README
│   ├── CLAUDE_legacy.md       # 옛 Track 1/2 분리 컨텍스트
│   ├── components/            # 옛 챗봇 UI 컴포넌트
│   └── prompts/               # 옛 페르소나 프롬프트
│
└── ml/                        # 회고 자산 (.claudeignore 차단, LoRA 어댑터 등)
```

---

## 4. 기술 스택 (요약)

| 레이어 | 기술 |
|---|---|
| Frontend | Next.js 16 App Router + TypeScript + Redux Toolkit + Tailwind 4 |
| Frontend SSE | `fetch` + `ReadableStream` 직접 파싱 (`lib/api/sse.ts`) |
| Backend | FastAPI (비동기) + Pydantic + SQLAlchemy + Alembic |
| Backend SSE | `StreamingResponse(media_type="text/event-stream")` |
| DB | PostgreSQL (asyncpg) — 단일 SaveSlot 테이블 |
| LLM | Gemma 4 31B (베이스, LoRA 미사용) on vLLM 0.19 (Phase 9) |
| 임베딩 | BGE-M3 small + HyDE (Phase 9) |
| 인프라 | RunPod A100 + Cloudflare Quick Tunnel (P0) / Tauri 패키징 (P2) |

---

## 5. 8개 백엔드 엔드포인트 (`/api/v1/`)

모두 `text/event-stream` SSE. 이벤트 타입: `metadata` / `delta` / `done` / `error`.

| 메서드 | 경로 | sLLM | 화면 |
|---|---|---|---|
| POST | `/respond` | Persona | 인터랙션 학습자 발화/[침묵] |
| POST | `/respond/auto` | Persona | 인터랙션 화면 진입 자동 발화 |
| POST | `/respond/farewell` | Persona | [작별을 고한다] 마지막 발화 |
| POST | `/explain` | Explain | [해설] [더 깊이 묻기] |
| POST | `/summarize` | Summary | Ep 1 → Ep 2 카운드오버 |
| GET / POST / DELETE | `/save` | Summary (POST 내부) | 단일 슬롯 |

자세한 요청/응답 스키마: `app/backend/README.md` 또는 `app/backend/schemas/vn.py`.

---

## 6. 시나리오별 함께 업로드할 파일

웹 LLM에서 *이 문서 + 다음 파일들*을 함께 올리면 해당 시나리오를 정밀하게 다룰 수 있다.

### "전체 흐름 / 컨셉 파악"
- `README.md` (루트)
- `docs/vn/HANDOFF_CONTEXT.md` (전체 컨셉 요약 + 폐기/유지 매트릭스)
- `docs/vn/VN_PROGRESS.md` (현재 진행 상태)

### "Phase 분할 / 작업 정의 이해"
- `docs/vn/VN_MIGRATION_PLAN.md` (Phase 0~9 모든 산출물 명세)

### "UI 동작 / 인터랙션 정책 검토"
- `docs/vn/VN_UI_POLICY.md` (페이드 타이밍, 모드 분리, 세이브 정책 등 단일 진실 소스)

### "Ep 1 본문 텍스트 / sLLM 프롬프트 분석"
- `docs/vn/EP1_TEXT_AND_PROMPTS.md` (화면별 정적 텍스트 + 시스템 프롬프트 변수)

### "Ep 2 본문 텍스트"
- *현재 docs/vn/에 EP2 마스터 문서 없음.* Ep 2 본문은 데이터 파일에 직접 들어가 있음:
  - `app/frontend/data/scenes/ep2_screen1_market_arrival.ts` (5단락)
  - `app/frontend/data/scenes/ep2_screen2_uebermensch.ts` (8단락)
  - `app/frontend/data/scenes/ep2_screen3_clown_fall.ts` (18단락)
  - `app/frontend/data/scenes/ep2_screen4_reunion.ts` (인터랙션 메타)
  - `app/frontend/data/scenes/ep2_ending.ts`

### "정적 풀이 (해설 패널) 텍스트 분석"
- `app/frontend/data/haeseol/ep1_screen{2,3,4}_*.ts`
- `app/frontend/data/haeseol/ep2_screen{1,2,3}_*.ts`
- (사용자 직접 작성, sLLM X)

### "프론트엔드 컴포넌트 작업"
- `app/frontend/CLAUDE.md` (컴포넌트 매트릭스)
- `app/frontend/app/globals.css` (디자인 토큰 + 스타일)
- 작업 대상 컴포넌트 (예: `components/vn/InteractionScreen.tsx`)

### "백엔드 sLLM 라우팅 작업"
- `app/backend/CLAUDE.md`
- `app/backend/BACKEND_STRUCTURE.md`
- `app/backend/services/sllm_clients.py` (Persona/Explain/Summary ABC + Mock + VLLM)
- `app/backend/services/llm_client.py` (저수준 추상)

### "Mock 응답 풀 / 시스템 프롬프트 검토"
- `app/backend/services/mock_data.py` (화면별 응답 풀)
- `app/backend/prompts/persona_v1.txt`
- `app/backend/prompts/explain_v1.txt`
- `app/backend/prompts/summary_v1.txt`

### "발표 시연 / 대본 검토"
- `demo/scenario_script.md` (사전 준비 + 발표 흐름 + 시연 포인트 매트릭스 + Q&A)

### "디자인 결정 / Phase 진행 회고"
- `docs/vn/VN_PROGRESS.md` (각 Phase의 *결정 사항* 섹션 + *알려진 한계*)

### "옛 컨텍스트 (회고)"
- `archived/README_legacy.md`, `archived/CLAUDE_legacy.md` (옛 상담 챗봇 컨셉)
- `app/PROGRESS.md` (4/13 중간 발표 회고)

### "일러스트 가이드 / 파일명 규약"
- `docs/vn/EP1_ILLUSTRATIONS.md` (8장 일러스트 컨셉 + 프롬프트 + 스타일)

---

## 7. 작품 용어집

| 용어 | 의미 | 등장 |
|---|---|---|
| 위버멘쉬 (Übermensch) | 인간을 넘어가는 자, 신이 죽은 자리에 새로운 가치를 만드는 존재 | Ep 2 #2 (선포) |
| 마지막 인간 (letzter Mensch) | 안락만을 추구, 위대함을 비웃고 모든 가치를 작게 만드는 인간 | Ep 2 #2 (위버멘쉬의 정반대) |
| 신의 죽음 | 절대적 가치가 무너졌다는 시대 진단 (단순 무신론 X) | Ep 1 #4 (프롤로그 클라이맥스) |
| 몰락 (Untergang) | 깨달은 자가 다시 사람들 사이로 내려가는 행위 | Ep 1 #2 |
| 밧줄 잠언 | "인간은 짐승과 위버멘쉬 사이에 매인 밧줄이다" | Ep 2 #3 |
| 차라투스트라 | 작품의 페르소나. 학습자의 동행자 + 가르치는 자 | 전체 |
| 학습자 / "그대" | 플레이어 캐릭터. 차라투스트라의 동행자 | Ep 1 #5~ |

## 8. 기술 용어집

| 용어 | 의미 |
|---|---|
| sLLM | "small LLM" — Gemma 4 31B 같은 중소형 모델. RAG로 보강. |
| Persona / Explain / Summary | 서로 다른 시스템 프롬프트로 호출되는 3종 sLLM 도메인 |
| Mock 모드 | 미리 짠 응답 풀에서 SSE 시뮬 (시연 안정성) |
| vLLM 모드 | 실제 RunPod GPU 추론 (Phase 9) |
| HyDE | Hypothetical Document Embeddings — 가상 문서 생성 후 임베딩으로 검색 |
| RAG | Retrieval-Augmented Generation — 검색 결과를 시스템 프롬프트에 주입 |
| 카운드오버 transition | Ep 1 → Ep 2 사이 시간 흐름 표현 + 백그라운드 요약 |
| 정적 풀이 / 동적 풀이 | 해설 패널의 *미리 작성된 손글씨* / *[더 깊이 묻기] sLLM 응답* |
| 책 삽화 레이아웃 | 16:10 캔버스 + 일러스트/텍스트 분할 + 세피아 톤 |

---

## 9. 자주 묻는 질문 시나리오

| 질문 | 어디 보면 답 있음 |
|---|---|
| "이 프로젝트가 뭐야?" | 이 문서 §1, `README.md` |
| "지금 어디까지 진행됐어?" | `docs/vn/VN_PROGRESS.md` 상단 *현재 상태 요약* |
| "어떻게 띄워?" | `README.md` Quick Start, `app/README.md` |
| "왜 이렇게 짰어?" | `docs/vn/VN_PROGRESS.md` 각 Phase의 *결정 사항* 섹션 |
| "Ep 1 본문 텍스트 보여줘" | `docs/vn/EP1_TEXT_AND_PROMPTS.md` §5 |
| "Ep 2 본문 텍스트는?" | `app/frontend/data/scenes/ep2_*.ts` (마스터 문서 없음) |
| "어떤 컴포넌트가 있어?" | `app/frontend/CLAUDE.md` 컴포넌트 매트릭스 |
| "백엔드 엔드포인트 목록?" | `app/backend/README.md`, `app/backend/CLAUDE.md` |
| "vLLM 실 연결은 어떻게?" | Phase 9 작업, `app/README.md` 모드 토글 + `archived/README_legacy.md` (RunPod 셋업) |
| "발표 시 무엇을 보여줘?" | `demo/scenario_script.md` |
| "디자인 토큰이 뭐야?" | `app/frontend/app/globals.css` 상단 + `app/frontend/CLAUDE.md` 디자인 토큰 |
| "강조 표시는 어떻게 작동?" | 본문 안 `**...**` 마크다운식 → `<em class="vn-emph">` (`NarrationScreen.tsx`의 `renderInline`) |
| "화면 전환 페이드는?" | `lib/hooks/useNavigate.ts` + `components/vn/TransitionOverlay.tsx` |
| "[저장]/[불러오기] 흐름?" | `lib/hooks/useSave.ts` + `app/page.tsx` (불러오기 모달) + `components/vn/InteractionScreen.tsx` (저장 모달) |
| "[해설] 패널 동작?" | `components/vn/HaeseolPanel.tsx` + `lib/hooks/useExplain.ts` + `data/haeseol/` |

---

## 10. 절대 건드리지 말 것 (외부 LLM도 동일)

- `archived/` 안 파일 — 회고 자산. 수정 시 발표 자료 손실.
- `app/PROGRESS.md` — 4/13 중간 발표 회고.
- `ml/` 디렉토리 — `.claudeignore` 차단된 회고 자산 (LoRA 어댑터, SFT 데이터 등).

---

## 11. 한 줄 요약

> 사용자 황철희(@HwangChulHee)의 학부 캡스톤 비주얼 노벨. Ep 1 + Ep 2 풀 사이클이 Mock 모드로 동작하며, Phase 9 (vLLM 실 연결)는 RunPod 환경 의존 별도 작업. 작품 결은 *책 삽화 레이아웃 + 세피아 톤 + 절제된 인터랙션*. 디자인 결정은 `docs/vn/VN_PROGRESS.md`에 누적.

---

## 부록 — 변경 이력

- 2026-05-01: 초안 작성. Phase 8 완료 시점 + 14개 커밋 origin/main 반영 시점.
